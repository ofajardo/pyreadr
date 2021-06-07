"""
@author: Otto Fajardo
"""
from collections import OrderedDict
import os
from urllib.request import urlopen

import pandas as pd

from ._pyreadr_parser import PyreadrParser, ListObjectsParser
from ._pyreadr_writer import PyreadrWriter
from .custom_errors import PyreadrError


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

    if hasattr(os, 'fsencode'):
        try:
            filename_bytes = os.fsencode(path)
        except UnicodeError:
            warnings.warn("file path could not be encoded with %s which is set as your system encoding, trying to encode it as utf-8. Please set your system encoding correctly." % sys.getfilesystemencoding())
            filename_bytes = os.fsdecode(path).encode("utf-8", "surrogateescape")
    else:
        if sys.version_info[0]>2:
            if type(path) == str:
                filename_bytes = path.encode('utf-8')
            elif type(path) == bytes:
                filename_bytes = path
            else:
                raise PyreadstatError("path must be either str or bytes")
        else:
            if type(path) not in (str, bytes, unicode):
                raise PyreadstatError("path must be str, bytes or unicode")
            filename_bytes = path.encode('utf-8')


    filename_bytes = os.path.expanduser(filename_bytes)
    if not os.path.isfile(filename_bytes):
        raise PyreadrError("File {0} does not exist!".format(filename_bytes))
    parser.parse(filename_bytes)

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
    if not isinstance(path, str):
        raise PyreadrError("path must be a string!")
    path = os.path.expanduser(path)
    if not os.path.isfile(path):
        raise PyreadrError("File {0} does not exist!".format(path))
 
    parser.parse(path)
    return parser.object_list
    
    
def write_rdata(path, df, df_name="dataset", dateformat="%Y-%m-%d", datetimeformat="%Y-%m-%d %H:%M:%S", compress=None):
    """
    Write a single pandas data frame to a rdata file.

    Parameters
    ----------
        path : str
            path to the file. The string is assumed to be utf-8 encoded.
        df : pandas data frame
            the dataframe to write
        df_name : str
            name for the R dataframe object, cannot be empty string. If 
            not supplied will default to "dataset"
        dateformat : str
            string to format datetime.date objects. 
            By default "%Y-%m-%d".
        datetimeformat : str
            string to format datetime like objects. By default "%Y-%m-%d %H:%M:%S".
    """
    
    if not df_name:
        msg = "df_name must be a valid string"
        raise PyreadrError(msg)
        
    if not isinstance(df, pd.DataFrame):
        msg = "df must be a pandas data frame"
        raise PyreadrError(msg)
    
    file_format = "rdata"
    writer = PyreadrWriter()

    if hasattr(os, 'fsencode'):
        try:
            filename_bytes = os.fsencode(path)
        except UnicodeError:
            warnings.warn("file path could not be encoded with %s which is set as your system encoding, trying to encode it as utf-8. Please set your system encoding correctly." % sys.getfilesystemencoding())
            filename_bytes = os.fsdecode(path).encode("utf-8", "surrogateescape")
    else:
        if sys.version_info[0]>2:
            if type(path) == str:
                filename_bytes = path.encode('utf-8')
            elif type(path) == bytes:
                filename_bytes = path
            else:
                raise PyreadstatError("path must be either str or bytes")
        else:
            if type(path) not in (str, bytes, unicode):
                raise PyreadstatError("path must be str, bytes or unicode")
            filename_bytes = path.encode('utf-8')

    filename_bytes = os.path.expanduser(filename_bytes)

    writer.write_r(filename_bytes, file_format, df, df_name, dateformat, datetimeformat, compress)


def write_rds(path, df, dateformat="%Y-%m-%d", datetimeformat="%Y-%m-%d %H:%M:%S", compress=None):
    """
    Write a single pandas data frame to a rds file.

    Parameters
    ----------
        path : str
            path to the file. The string is assumed to be utf-8 encoded.
        df : pandas data frame
            the dataframe to write
        dateformat : str
            string to format datetime.date objects. 
            By default "%Y-%m-%d".
        datetimeformat : str
            string to format datetime like objects. By default "%Y-%m-%d %H:%M:%S".
        compress : str
            compression to use, defaults to no compression. Only "gzip" supported.
    """
    
    if not isinstance(df, pd.DataFrame):
        msg = "df must be a pandas data frame"
        raise PyreadrError(msg)
    
    file_format = "rds"
    df_name = ""   # this is irrelevant in this case, but we need to pass something
    
    if hasattr(os, 'fsencode'):
        try:
            filename_bytes = os.fsencode(path)
        except UnicodeError:
            warnings.warn("file path could not be encoded with %s which is set as your system encoding, trying to encode it as utf-8. Please set your system encoding correctly." % sys.getfilesystemencoding())
            filename_bytes = os.fsdecode(path).encode("utf-8", "surrogateescape")
    else:
        if sys.version_info[0]>2:
            if type(path) == str:
                filename_bytes = path.encode('utf-8')
            elif type(path) == bytes:
                filename_bytes = path
            else:
                raise PyreadstatError("path must be either str or bytes")
        else:
            if type(path) not in (str, bytes, unicode):
                raise PyreadstatError("path must be str, bytes or unicode")
            filename_bytes = path.encode('utf-8')

    filename_bytes = os.path.expanduser(filename_bytes)

    writer = PyreadrWriter()
    writer.write_r(filename_bytes, file_format, df, df_name, dateformat, datetimeformat, compress)

def download_file(url, destination_path):
    """
    Downloads a file from a web url to destination_path.

    Parameters
    ----------
    url : str
        url of the file
    destination_path : str
        path to write the file to disk

    Returns
    -------
    str
        it gives back the path to where the file was written.
    """
    response = urlopen(url)
    content = response.read()
    if destination_path.startswith("~"):
        destination_path = os.path.expanduser(destination_path)
    with open(destination_path, 'wb') as fhandle:
        try:
            fhandle.write(content)
        except:
            raise
    return destination_path
