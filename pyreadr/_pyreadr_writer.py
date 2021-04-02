"""
@author: Otto Fajardo
"""

from collections import OrderedDict
import datetime
import gzip
import os
import shutil

import numpy as np
import pandas as pd

from .librdata import Writer
from .custom_errors import PyreadrError


# configuration

int_types = {np.dtype('int32'), np.dtype('int16'), np.dtype('int8'), np.dtype('uint8'), np.dtype('uint16'),
             np.int32, np.int16, np.int8, np.uint8, np.uint16}
int_mixed_types = {pd.Int8Dtype(), pd.Int16Dtype(), pd.Int32Dtype(), pd.UInt8Dtype(), pd.UInt16Dtype()}
float_types = {np.dtype('int64'), np.dtype('uint64'), np.dtype('uint32'), np.dtype('float'),
               np.int64, np.uint64, np.uint32, np.float, pd.Int64Dtype(), pd.UInt32Dtype(), pd.UInt64Dtype()}
datetime_types = {datetime.datetime, np.datetime64}

pyreadr_to_librdata_types = {"INTEGER": "INTEGER", "NUMERIC": "NUMERIC",
                        "LOGICAL": "LOGICAL", "CHARACTER": "CHARACTER",
                        "OBJECT": "CHARACTER", "DATE": "CHARACTER",
                        "DATETIME":"CHARACTER"}
                        
librdata_min_integer = -2147483648


def get_pyreadr_column_types(df):
    """
    From a pandas data frame, get an OrderedDict with column name as key
    and pyreadr column type as value, and also a list with boolean 
    values indicating if the column has missing values (np.nan).
    The pyreadr column types are needed for downstream processing.
    """

    types = df.dtypes.values.tolist()
    columns = df.columns.values.tolist()

    result = OrderedDict()
    has_missing_values = [False] * len(columns)
    for indx, (col_name, col_type) in enumerate(zip(columns, types)):
        
        # recover original type for categories
        if type(col_type) is pd.core.dtypes.dtypes.CategoricalDtype:
            col_type = np.asarray(df[col_name]).dtype
        
        if col_type in int_types:
            result[col_name] = "INTEGER"
        elif col_type in float_types:
            result[col_name] = "NUMERIC"
        elif col_type == bool:
            result[col_name] = "LOGICAL"
        # np.datetime64[ns]
        elif col_type == np.dtype('<M8[ns]') or col_type == np.datetime64:
                result[col_name] = "DATETIME"
                missing = pd.isna(df[col_name])
                if np.any(missing):
                    has_missing_values[indx] = True
        elif col_type == object or col_type in int_mixed_types:
            missing = pd.isna(df[col_name])
            if np.any(missing):
                has_missing_values[indx] = True
                if col_type in int_mixed_types:
                    result[col_name] = "INTEGER"
                    continue
                col = df[col_name].dropna()
                if len(col):
                    curtype = type(col.iloc[0])
                    equal = np.array(col.apply(lambda x: type(x) == curtype))
                    if not np.all(equal):
                        result[col_name] = "OBJECT"
                        continue
                else:
                    result[col_name] = "LOGICAL"
                    continue
            else:
                if col_type in int_mixed_types:
                    result[col_name] = "INTEGER"
                    continue
                curtype = type(df[col_name][0])
                equal = np.array(df[col_name].apply(lambda x: type(x) == curtype))
                if not np.all(equal):
                    result[col_name] = "OBJECT"
                    continue
            
            if curtype in int_types:
                result[col_name] = "INTEGER"
            elif curtype in float_types:
                result[col_name] = "NUMERIC"
            elif curtype == bool:
                result[col_name] = "LOGICAL"
            elif curtype == str:
                result[col_name] = "CHARACTER"
            elif curtype == datetime.date:
                result[col_name] = "DATE"
            elif curtype == datetime.datetime:
                result[col_name] = "DATETIME"
            else:
                result[col_name] = "OBJECT"
            
        else:
            # generic object
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


def transform_data(pd_series, dtype, has_missing, dateformat, datetimeformat):
    """
    Get a column (pd.Series), pyreadr type (dtype) and boolean indicating
    wheter there are missing values and transform the values to values
    compatible with librdata.
    dateformat and datetimeformat are strings used to format dates and
    datetimes to strings.
    """

    if dtype == "INTEGER":
        pd_series = pd_series.astype("Int32") # if int8 setting min_integer would cause overflow
        if has_missing:
            pd_series.loc[pd.isna(pd_series)] = librdata_min_integer
        pd_series = pd_series.astype(np.int32)
    elif dtype == "NUMERIC":
        pass
    elif dtype == "LOGICAL":
        if type(pd_series.dtype) is pd.core.dtypes.dtypes.CategoricalDtype:
            pd_series = pd_series.astype('object')
        if has_missing:
            pd_series.loc[pd.isna(pd_series)] = librdata_min_integer
        pd_series = pd_series.astype(np.int32)
    elif dtype == "CHARACTER":
        pass
    elif dtype == "OBJECT":
        if type(pd_series.dtype) is pd.core.dtypes.dtypes.CategoricalDtype:
            pd_series = pd_series.astype('object')
        pd_series.loc[pd.notnull(pd_series)] = pd_series.loc[pd.notnull(pd_series)].apply(lambda x: str(x))
    elif dtype == "DATE":
        if type(pd_series.dtype) is pd.core.dtypes.dtypes.CategoricalDtype:
            pd_series = pd_series.astype('object')
        # for now transforming to string
        # potentially dates could be transformed to true DATE type in R using rdata_append_date_value
        # for this, datetime.date must be trasnformed to a tm struct for example:
        # https://stackoverflow.com/questions/39673816/want-to-perform-date-time-value-manipulation-using-struct-tm
        pd_series.loc[pd.notnull(pd_series)] = pd_series.loc[pd.notnull(pd_series)].apply(lambda x: x.strftime(dateformat))
    elif dtype == "DATETIME":
        if type(pd_series.dtype) is pd.core.dtypes.dtypes.CategoricalDtype:
            pd_series = pd_series.astype('object')
        # transforming to string to avoid issues with timezones
        pd_series.loc[pd.notnull(pd_series)] = pd_series.loc[pd.notnull(pd_series)].apply(lambda x: x.strftime(datetimeformat))
    else:
        msg = "Unkown pyreadr data type"
        raise PyreadrError(msg)
        
    return pd_series


class PyreadrWriter(Writer):

    def compress_file(self, src, dst, compression="gzip"):
        """
        Compresses a file from src to dst with given compression
        """
        if compression == "gzip":
            try:
                with open(src, "rb") as fin:
                    try:
                        with gzip.open(dst, "wb") as fout:
                            shutil.copyfileobj(fin, fout)
                    except:
                        raise
            except:
                raise
        else:
            raise PyreadrError("compression {0} not implemented!".format(compression))

    
    def write_r(self, path, file_format, df, df_name, dateformat, datetimeformat, compress):
        """
        write a RData or Rds file. 
        path: str: path to the file
        file_format: str: rdata or rds
        df: pandas data frame
        df_name = name of the object to write. Irrelevant if rds format.
        dateformat: str: string to format dates
        datetimeformat: str: string to format datetimes
        compress: str: compression to use, for now only gzip supported.
        """
        
        col_names = df.columns.tolist()
        pyreadr_types, hasmissing = get_pyreadr_column_types(df)
        librdata_types = pyreadr_types_to_librdata_types(pyreadr_types)
        original_path = path
        
        if compress:
            path = original_path + "_temp"
            if compress != "gzip":
                PyreadrError("compression {0} not implemented!, Please use gzip".format(compress))

        self.open(path, file_format)
        self.set_row_count(df.shape[0])
        self.set_table_name(df_name)
        for col_name in col_names:
            curtype = librdata_types[col_name]
            self.add_column(str(col_name), curtype)
            
        for indx, column in enumerate(df):
            col = df[column].copy()
            tcol = transform_data(col, pyreadr_types[column], hasmissing[indx], dateformat, datetimeformat)
            tcol = tcol.values.tolist()
            curtype = librdata_types[column]
            for row_indx, val in enumerate(tcol):
                self.insert_value(row_indx, indx, val, curtype)
            
        self.close()

        if compress:
            self.compress_file(path, original_path, compress)
            os.remove(path)
