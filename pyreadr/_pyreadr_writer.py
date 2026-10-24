"""
@author: Otto Fajardo
"""

from collections import OrderedDict
from collections.abc import Mapping
import datetime
import gzip
import os
import shutil
import struct

import numpy as np
import narwhals.stable.v2 as nw

# pandas is optional, pd.NA is its missing value marker for nullable types
try:
    from pandas import NA as pandas_na
except ImportError:
    pandas_na = None

from .librdata import Writer
from .custom_errors import PyreadrError


# configuration

pyreadr_to_librdata_types = {"INTEGER": "INTEGER", "NUMERIC": "NUMERIC",
                        "LOGICAL": "LOGICAL", "CHARACTER": "CHARACTER",
                        "OBJECT": "CHARACTER", "DATE": "CHARACTER",
                        "DATETIME":"CHARACTER", "FACTOR": "INTEGER"}

librdata_min_integer = -2147483648
# R's NA for doubles (NA_real_): a NaN with 1954 in the low word. A plain NaN is NaN in R, not NA
r_na_real = struct.unpack("<d", struct.pack("<Q", 0x7FF00000000007A2))[0]


def is_missing(value):
    """
    True for the missing value markers None (polars null, object columns) and pd.NA. NaN is not missing here, as
    it is a valid double: numpy float NaN is written as NaN.
    """
    return value is None or (pandas_na is not None and value is pandas_na)


def is_nan(value):
    """
    True for float NaN (including numpy float64)
    """
    return isinstance(value, float) and value != value


def is_object_column(nw_series):
    """
    True for untyped columns whose type has to be decided from the values. pandas object columns count even if
    narwhals infers another type for them (e.g. String for a column with only missing values), unless they have
    no rows: then there are no values to decide from and the type inferred by narwhals is kept (in pandas 2
    dtype=str gives object, an empty string column has to stay character).
    """
    if nw_series.dtype == nw.Object:
        return True
    return (nw_series.implementation.is_pandas_like() and nw_series.to_native().dtype == object
            and len(nw_series) > 0)


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

        # polars columns with only nulls have the Null type (narwhals Unknown): logical as in R
        if is_object_column(curseries):
            col_type = nw.Object
        elif col_type == nw.Unknown and curseries.null_count() == len(curseries):
            result[col_name] = "LOGICAL"
            continue

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
            non_null = [x for x in lst if not is_missing(x)]
            if not non_null:
                result[col_name] = "LOGICAL"
                continue
            # np.nan is the pandas missing value in object columns of other types (e.g. R integer or logical
            # columns with NA are read as object with NaN): it decides the type only if there is nothing else, and
            # stays NaN only in float columns
            typed = [x for x in non_null if not is_nan(x)] or non_null
            curtype = type(typed[0])
            if not all(type(x) == curtype for x in typed):
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

    # in non float columns NaN is missing (object columns, see get_pyreadr_column_types)
    if dtype == "INTEGER":
        if is_object_column(nw_series):
            lst = nw_series.to_list()
            return [librdata_min_integer if is_missing(x) or is_nan(x) else int(x) for x in lst]
        return nw_series.fill_null(librdata_min_integer).cast(nw.Int32).to_list()

    elif dtype == "NUMERIC":
        # missing (polars null, pd.NA, None) is R's NA, NaN stays NaN
        lst = nw_series.to_list()
        return [r_na_real if is_missing(x) else x for x in lst]

    elif dtype == "LOGICAL":
        if is_object_column(nw_series) or nw_series.dtype == nw.Unknown:
            lst = nw_series.to_list()
            return [librdata_min_integer if is_missing(x) or is_nan(x) else int(x) for x in lst]
        return nw_series.cast(nw.Int32).fill_null(librdata_min_integer).to_list()

    elif dtype == "CHARACTER":
        lst = nw_series.to_list()
        return [None if is_missing(x) or is_nan(x) else x for x in lst]

    elif dtype == "FACTOR":
        # R factor codes are 1-based
        codes = {level: i + 1 for i, level in enumerate(get_factor_levels(nw_series))}
        return [codes.get(x, librdata_min_integer) for x in nw_series.to_list()]

    elif dtype == "OBJECT":
        lst = nw_series.to_list()
        return [None if is_missing(x) or is_nan(x) else str(x) for x in lst]

    elif dtype == "DATE":
        lst = nw_series.to_list()
        return [None if is_missing(x) or x != x else x.strftime(dateformat) for x in lst]

    elif dtype == "DATETIME":
        lst = nw_series.to_list()
        return [None if is_missing(x) or x != x else x.strftime(datetimeformat) for x in lst]

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


def get_frames_to_write(df, df_name, rownames_column, allow_multiple):
    """
    Normalize the data frames to write into a list of tuples (name, df, rownames_column), one per R object.
    df: pandas or polars data frame, or (if allow_multiple) a dict name -> data frame
    df_name: str: name of the object if df is a single data frame
    rownames_column: None, str or (if df is a dict) dict name -> column. With multiple data frames a str applies
        to the data frames that have that column.
    allow_multiple: bool: False for rds, which holds one object
    """
    if isinstance(df, Mapping):
        if not allow_multiple:
            raise PyreadrError("a Rds file holds one object, df must be a single pandas or polars DataFrame")
        if not df:
            raise PyreadrError("df must contain at least one data frame")
        for name in df:
            if not isinstance(name, str) or not name:
                raise PyreadrError("data frame names must be non-empty strings, got {0!r}".format(name))
        frames = list(df.items())
    else:
        if isinstance(rownames_column, Mapping):
            raise PyreadrError("rownames_column can be a dict only if df is a dict of data frames")
        frames = [(df_name, df)]

    nw_frames = []
    for name, frame in frames:
        try:
            nw_frames.append(nw.from_native(frame, eager_only=True))
        except nw.exceptions.DuplicateError:
            # pandas allows duplicate column names, narwhals does not
            columns = list(frame.columns)
            duplicates = sorted({str(c) for c in columns if columns.count(c) > 1})
            raise PyreadrError("duplicate column names are not supported: {0}".format(duplicates))
        except Exception:
            if isinstance(df, Mapping):
                raise PyreadrError("{0} must be a pandas or polars DataFrame".format(name))
            raise PyreadrError("df must be a pandas or polars DataFrame")

    if isinstance(rownames_column, Mapping):
        unknown = [name for name in rownames_column if name not in df]
        if unknown:
            raise PyreadrError("rownames_column has data frames not in df: {0}".format(unknown))
        rownames_columns = [rownames_column.get(name) for name, _ in frames]
    elif rownames_column is not None and isinstance(df, Mapping):
        rownames_columns = [rownames_column if rownames_column in nw_df.columns else None for nw_df in nw_frames]
        if all(x is None for x in rownames_columns):
            raise PyreadrError("rownames_column {0} not found in any data frame".format(rownames_column))
    else:
        rownames_columns = [rownames_column] * len(frames)

    return [(name, frame, rn) for (name, frame), rn in zip(frames, rownames_columns)]


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


    def write_table(self, name, nw_df, row_names, dateformat, datetimeformat):
        """
        write one data frame as a table into the open file.
        name: str: name of the R object. Irrelevant if rds format.
        nw_df: narwhals data frame
        row_names: list of str or None
        """
        col_names = nw_df.columns
        pyreadr_types, hasmissing = get_pyreadr_column_types(nw_df)
        librdata_types = pyreadr_types_to_librdata_types(pyreadr_types)

        self.new_table(name, nw_df.shape[0], row_names)
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

        self.end_table()

    def write_r(self, path, file_format, frames, dateformat, datetimeformat, compress, compresslevel=9):
        """
        write a RData or Rds file.
        path: str: path to the file
        file_format: str: rdata or rds
        frames: list of tuples (name, df, rownames_column) as returned by get_frames_to_write, one per R object.
            name: name of the object, irrelevant if rds format. df: pandas or polars data frame. rownames_column:
            name of the column to write as row names; if None, the index of a pandas data frame is written as row
            names unless it is the default RangeIndex.
        dateformat: str: string to format dates
        datetimeformat: str: string to format datetimes
        compress: str: compression to use, for now only gzip supported.
        compresslevel: int: compression level for gzip (1-9), default 9.
        """

        # prepare (and validate) all frames before writing anything
        tables = []
        for name, df, rownames_column in frames:
            nw_df = nw.from_native(df, eager_only=True)
            row_names, nw_df = get_row_names(df, nw_df, rownames_column)
            tables.append((name, nw_df, row_names))
        original_path = path

        if compress:
            path = original_path + b"_temp"
            if compress != "gzip":
                raise PyreadrError("compression {0} not implemented!, Please use gzip".format(compress))

        self.open(path, file_format)
        try:
            for name, nw_df, row_names in tables:
                self.write_table(name, nw_df, row_names, dateformat, datetimeformat)
        except:
            self.close(complete=False)
            raise
        self.close()

        if compress:
            self.compress_file(path, original_path, compress, compresslevel)
            os.remove(path)
