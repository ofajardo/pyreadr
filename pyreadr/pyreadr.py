"""
@author: Otto Fajardo
"""
from collections import OrderedDict

from pyreadr._pyreadr_parser import PyreadrParser, ListObjectsParser


def read_r(path, use_objects=None, timezone=None):
    """
    Read an R RData or Rds file into pandas data frames

    Parameters
    ----------
        path : str
            path to the file. The string is assumed to be utf-8 encoded.
        use_objects : list, optional
            a list with object names to read from the file. Only those objects will be imported. Case sensitive!
        timezone : str, optional
            timezone to localize datetimes, UTC otherwise.
            R datetimes (POSIXct and POSIXlt) are stored as UTC, but coverted to some timezone (explicitly if set by the
            user or implicitly to local zone) when displaying it in R. librdata cannot recover that timezone information
            therefore timestamps are displayed in UTC, unless this parameter is set.

    Returns
    -------
        result : OrderedDict
            object name as key and pandas data frame as value
    """

    parser = PyreadrParser()
    if use_objects:
        parser.set_use_objects(use_objects)
    if timezone:
        parser.set_timezone(timezone)
    parser.parse(path)

    result = OrderedDict()
    for table_index, table in enumerate(parser.table_data):
        result[table.name] = table.convert_to_pandas_dataframe()
    return result


def list_objects(path):
    """
    Read an R RData or Rds file and lists objects and their column names.
    Not all objects are readable, and also it is not always possible to read the column names without parsing the
    whole file, in those cases this method will return Nones instead of column names.

    Parameters
    ----------
        path : str
            path to the file. The string is assumed to be utf-8 encoded.

    Returns
    -------
        result : list
            a list of dictionaries, where each dictionary has a key "object_name" with the name of the object and
            columns with a list of columns.
    """

    parser = ListObjectsParser()
    parser.parse(path)
    return parser.object_list
