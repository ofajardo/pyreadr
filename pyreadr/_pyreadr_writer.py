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
                        "DATETIME":"CHARACTER"}

librdata_min_integer = -2147483648


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

        # Categorical: unwrap to underlying categories dtype, then fall through
        if col_type == nw.Categorical:
            col_type = curseries.cat.get_categories().dtype

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
        elif col_type == nw.Object or isinstance(col_type, nw.Enum):
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


    def write_r(self, path, file_format, df, df_name, dateformat, datetimeformat, compress, compresslevel=9):
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
        """

        nw_df = nw.from_native(df, eager_only=True)
        col_names = nw_df.columns
        pyreadr_types, hasmissing = get_pyreadr_column_types(nw_df)
        librdata_types = pyreadr_types_to_librdata_types(pyreadr_types)
        original_path = path

        if compress:
            path = original_path + b"_temp"
            if compress != "gzip":
                PyreadrError("compression {0} not implemented!, Please use gzip".format(compress))

        self.open(path, file_format)
        self.set_row_count(nw_df.shape[0])
        self.set_table_name(df_name)
        for col_name in col_names:
            self.add_column(str(col_name), librdata_types[col_name])

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
