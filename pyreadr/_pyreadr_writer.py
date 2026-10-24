"""
@author: Otto Fajardo
"""

from collections import OrderedDict
import datetime
import gzip
import os
import shutil

import numpy as np
import narwhals.stable.v2 as nw

from .librdata import Writer
from .custom_errors import PyreadrError


# configuration

pyreadr_to_librdata_types = {"INTEGER": "INTEGER", "NUMERIC": "NUMERIC",
                        "LOGICAL": "LOGICAL", "CHARACTER": "CHARACTER",
                        "OBJECT": "CHARACTER", "DATE": "CHARACTER",
                        "DATETIME":"CHARACTER", "FACTOR": "INTEGER"}

librdata_min_integer = -2147483648


def get_factor_levels(nw_series):
    """
    From a narwhals categorical or enum series, get the list of levels to write as R factor levels.
    """
    # polars Categorical categories are global (shared by all categorical columns), take the levels from the data,
    # sorted as R's factor() does. pandas categories and polars Enum are per column and keep their order.
    if nw_series.dtype == nw.Categorical and nw_series.implementation.is_polars():
        return sorted(nw_series.drop_nulls().unique().cast(nw.String).to_list())
    return nw_series.cat.get_categories().to_list()


def get_pyreadr_column_types(nw_df):
    """
    From a narwhals data frame, get an OrderedDict with column name as key
    and pyreadr column type as value, and also a list with boolean
    values indicating if the column has missing values.
    """

    result = OrderedDict()
    has_missing_values = []

    for curseries in nw_df.iter_columns():
        col_name = curseries.name
        col_type = curseries.dtype
        has_missing = bool(curseries.is_null().any())
        has_missing_values.append(has_missing)

        # Categorical and Enum: string categories become R factors, otherwise unwrap to the underlying categories
        # dtype, then fall through
        if col_type == nw.Categorical or isinstance(col_type, nw.Enum):
            categories = curseries.cat.get_categories()
            if categories.dtype == nw.String and len(get_factor_levels(curseries)) > 0:
                result[col_name] = "FACTOR"
                continue
            col_type = categories.dtype

        if col_type in (nw.Int8, nw.Int16, nw.Int32, nw.UInt8, nw.UInt16):
            result[col_name] = "INTEGER"
        elif col_type in (nw.Int64, nw.UInt32, nw.UInt64, nw.Float32, nw.Float64):
            result[col_name] = "NUMERIC"
        elif col_type == nw.Boolean:
            result[col_name] = "LOGICAL"
        elif col_type == nw.String:
            result[col_name] = "CHARACTER"
        elif isinstance(col_type, nw.Datetime):
            result[col_name] = "DATETIME"
        elif col_type == nw.Date:
            result[col_name] = "DATE"
        elif col_type == nw.Object:
            lst = curseries.to_list()
            non_null = [x for x in lst if x is not None]
            if not non_null:
                result[col_name] = "LOGICAL"
                continue
            curtype = type(non_null[0])
            if not all(type(x) == curtype for x in non_null):
                result[col_name] = "OBJECT"
                continue
            if curtype in (int, np.int8, np.int16, np.int32, np.int64,
                           np.uint8, np.uint16, np.uint32, np.uint64):
                result[col_name] = "INTEGER"
            elif curtype == float:
                result[col_name] = "NUMERIC"
            elif curtype == bool:
                result[col_name] = "LOGICAL"
            elif curtype == str:
                result[col_name] = "CHARACTER"
            elif issubclass(curtype, datetime.datetime):
                result[col_name] = "DATETIME"
            elif issubclass(curtype, datetime.date):
                result[col_name] = "DATE"
            else:
                result[col_name] = "OBJECT"
        else:
            result[col_name] = "OBJECT"

    return result, has_missing_values


def pyreadr_types_to_librdata_types(pyreadr_types):
    """
    Transform pyreadr types to data types compatible with librdata
    """

    result = OrderedDict()
    for key, value in pyreadr_types.items():
        result[key] = pyreadr_to_librdata_types[value]

    return result


def transform_data(nw_series, dtype, has_missing, dateformat, datetimeformat):
    """
    Get a narwhals Series, pyreadr type (dtype) and boolean indicating
    whether there are missing values and transform the values to a list
    of primitives compatible with librdata.
    """

    if dtype == "INTEGER":
        if nw_series.dtype == nw.Object:
            lst = nw_series.to_list()
            return [int(x) if x is not None else librdata_min_integer for x in lst]
        return nw_series.fill_null(librdata_min_integer).cast(nw.Int32).to_list()

    elif dtype == "NUMERIC":
        lst = nw_series.to_list()
        return [float('nan') if x is None else x for x in lst]

    elif dtype == "LOGICAL":
        if nw_series.dtype == nw.Object:
            lst = nw_series.to_list()
            return [int(x) if x is not None else librdata_min_integer for x in lst]
        return nw_series.cast(nw.Int32).fill_null(librdata_min_integer).to_list()

    elif dtype == "CHARACTER":
        return nw_series.to_list()

    elif dtype == "FACTOR":
        # R factor codes are 1-based
        codes = {level: i + 1 for i, level in enumerate(get_factor_levels(nw_series))}
        return [codes.get(x, librdata_min_integer) for x in nw_series.to_list()]

    elif dtype == "OBJECT":
        lst = nw_series.to_list()
        return [str(x) if x is not None else None for x in lst]

    elif dtype == "DATE":
        lst = nw_series.to_list()
        return [x.strftime(dateformat) if x is not None and x == x else None for x in lst]

    elif dtype == "DATETIME":
        lst = nw_series.to_list()
        return [x.strftime(datetimeformat) if x is not None and x == x else None for x in lst]

    else:
        raise PyreadrError("Unknown pyreadr data type")


def get_row_names(df, nw_df, rownames_column):
    """
    Get the row names to write. They come from the column rownames_column if given, otherwise from the index
    of a pandas data frame if it is not the default RangeIndex.
    df: native data frame
    nw_df: narwhals data frame
    rownames_column: str or None: name of the column to use as row names
    returns a tuple (row_names, nw_df), where row_names is a list of str or None and nw_df is the narwhals data
        frame without the rownames_column
    """
    if rownames_column is not None:
        if rownames_column not in nw_df.columns:
            raise PyreadrError("rownames_column {0} not found in the data frame".format(rownames_column))
        if nw_df[rownames_column].is_null().any():
            raise PyreadrError("row names cannot contain missing values")
        row_names = nw_df[rownames_column].to_list()
        nw_df = nw_df.drop(rownames_column)
    elif nw_df.implementation.is_pandas():
        index = df.index
        if index.nlevels > 1:
            raise PyreadrError("a MultiIndex cannot be written as row names, reset the index or use rownames_column")
        pd = nw.get_native_namespace(nw_df)
        if isinstance(index, pd.RangeIndex) and index.start == 0 and index.step == 1:
            return None, nw_df
        if index.hasnans:
            raise PyreadrError("row names cannot contain missing values")
        row_names = index.to_list()
    else:
        return None, nw_df

    row_names = [str(x) for x in row_names]
    if len(set(row_names)) != len(row_names):
        raise PyreadrError("row names cannot contain duplicates")
    return row_names, nw_df


class PyreadrWriter(Writer):

    def compress_file(self, src, dst, compression="gzip", compresslevel=9):
        """
        Compresses a file from src to dst with given compression
        """
        if compression == "gzip":
            try:
                with open(src, "rb") as fin:
                    try:
                        with gzip.open(dst, "wb", compresslevel=compresslevel) as fout:
                            shutil.copyfileobj(fin, fout, length=1024 * 1024)
                    except:
                        raise
            except:
                raise
        else:
            raise PyreadrError("compression {0} not implemented!".format(compression))


    def write_r(self, path, file_format, df, df_name, dateformat, datetimeformat, compress, compresslevel=9,
                rownames_column=None):
        """
        write a RData or Rds file.
        path: str: path to the file
        file_format: str: rdata or rds
        df: pandas or polars data frame
        df_name = name of the object to write. Irrelevant if rds format.
        dateformat: str: string to format dates
        datetimeformat: str: string to format datetimes
        compress: str: compression to use, for now only gzip supported.
        compresslevel: int: compression level for gzip (1-9), default 9.
        rownames_column: str: name of the column to write as row names. If None, the index of a pandas data
            frame is written as row names unless it is the default RangeIndex.
        """

        nw_df = nw.from_native(df, eager_only=True)
        row_names, nw_df = get_row_names(df, nw_df, rownames_column)
        col_names = nw_df.columns
        pyreadr_types, hasmissing = get_pyreadr_column_types(nw_df)
        librdata_types = pyreadr_types_to_librdata_types(pyreadr_types)
        original_path = path

        if compress:
            path = original_path + b"_temp"
            if compress != "gzip":
                raise PyreadrError("compression {0} not implemented!, Please use gzip".format(compress))

        self.open(path, file_format)
        self.set_row_count(nw_df.shape[0])
        self.set_table_name(df_name)
        if row_names is not None:
            self.set_row_names(row_names)
        for col_name in col_names:
            column = self.add_column(str(col_name), librdata_types[col_name])
            if pyreadr_types[col_name] == "FACTOR":
                column.add_level_labels(get_factor_levels(nw_df[col_name]))

        for indx, col_name in enumerate(col_names):
            nw_series = nw_df[col_name]
            tcol = transform_data(nw_series, pyreadr_types[col_name], hasmissing[indx],
                                  dateformat, datetimeformat)
            curtype = librdata_types[col_name]
            for row_indx, val in enumerate(tcol):
                self.insert_value(row_indx, indx, val, curtype)

        self.close()

        if compress:
            self.compress_file(path, original_path, compress, compresslevel)
            os.remove(path)
