"""
@author: Otto Fajardo
"""
from collections import OrderedDict
from collections.abc import Mapping
import os
import sys
from urllib.request import urlopen
import warnings

import narwhals.stable.v2 as nw

from ._pyreadr_parser import PyreadrParser, ListObjectsParser, MetadataParser
from ._pyreadr_writer import PyreadrWriter, get_frames_to_write
from .custom_errors import PyreadrError


def _encode_path(path):
    """
    File path (str, bytes or Path) as bytes for the C layer, with ~ expanded.
    """
    try:
        filename_bytes = os.fsencode(path)
    except UnicodeError:
        warnings.warn("file path could not be encoded with %s which is set as your system encoding, trying to encode it as utf-8. Please set your system encoding correctly." % sys.getfilesystemencoding())
        filename_bytes = os.fsdecode(path).encode("utf-8", "surrogateescape")
    return os.path.expanduser(filename_bytes)


def _parse(parser, path):
    """
    Parse a file path (str, bytes or Path) or a file-like object with read() and seek() methods.
    """
    if hasattr(path, 'read') and hasattr(path, 'seek'):
        parser.parse(b"", file_object=path)
    else:
        filename_bytes = _encode_path(path)
        if not os.path.isfile(filename_bytes):
            raise PyreadrError("File {0} does not exist!".format(filename_bytes))
        parser.parse(filename_bytes)


def read_r(path, use_objects=None, timezone=None, output_format="pandas", encoding=None, row_offset=0, row_limit=0):
    """
    Read an R RData or Rds file into pandas or polars data frames.

    Parameters
    ----------
        path : str, bytes, Path, or file-like object
            path to the file, or a file-like object with read() and seek() methods (e.g. io.BytesIO).
            String paths are assumed to be utf-8 encoded.
        use_objects : list, optional
            a list with object names to read from the file. Only those objects will be imported. Case sensitive!
        timezone : str, optional
            timezone to localize datetimes, UTC otherwise.
            R datetimes (POSIXct and POSIXlt) are stored as UTC, but converted to some timezone (explicitly if set by the
            user or implicitly to local zone) when displaying it in R. librdata cannot recover that timezone information
            therefore timestamps are displayed in UTC, unless this parameter is set.
        output_format : str, optional
            format of the output data frames. "pandas" (default) or "polars".
        encoding : str, optional
            encoding of strings that have no encoding mark in the file, for example "latin1" or "WINDOWS-1252".
            It overrides the encoding declared in the file (version 3 files) or supplies it (version 2 files).
            Strings explicitly marked as UTF-8 or latin1 in the file are not affected. Set it if reading
            fails with a UnicodeDecodeError.
        row_offset : int, optional
            number of rows to skip at the beginning, 0 by default. Applies to every object read.
        row_limit : int, optional
            maximal number of rows to read, 0 (default) reads all rows. Applies to every object read. R stores
            data by column, so the columns are still read completely from the file, but only the selected rows
            are kept, which reduces the memory needed.

    Returns
    -------
        result : OrderedDict
            object name as key and pandas or polars data frame as value.
    """

    if output_format not in ("pandas", "polars"):
        raise PyreadrError("output_format must be 'pandas' or 'polars'")
    if encoding is not None and not isinstance(encoding, str):
        raise PyreadrError("encoding must be a string")
    for name, value in (("row_offset", row_offset), ("row_limit", row_limit)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise PyreadrError("{0} must be a non-negative integer".format(name))

    parser = PyreadrParser()
    if use_objects:
        parser.set_use_objects(use_objects)
    if timezone:
        parser.set_timezone(timezone)
    if encoding:
        parser.set_encoding(encoding)
    parser.set_output_format(output_format)
    parser.set_rows(row_offset, row_limit)
    _parse(parser, path)
    parser.finish_text_column()

    result = OrderedDict()
    for table_index, table in enumerate(parser.table_data):
        result[table.name] = table.convert_to_dataframe()
    if not result:
        if use_objects:
            msg = "no readable objects with the names in use_objects were found in the file."
        else:
            msg = "the file has no readable objects (data frames, vectors, matrices or arrays)."
        warnings.warn(msg + " Lists, S4 objects and other unsupported objects are skipped.")
    return result


def read_metadata(path):
    """
    Read the header of an R RData or Rds file: file type, serialization format version, compression and R
    versions. Only the beginning of the file is read, the data is not.

    Parameters
    ----------
        path : str, bytes, Path, or file-like object
            path to the file, or a file-like object with read() and seek() methods (e.g. io.BytesIO).

    Returns
    -------
        result : dict
            file_type: "RData" or "Rds".
            format_version: serialization format version, 2 or 3 (R >= 3.5 writes 3 by default).
            compression: "gzip", "bzip2", "xz" or None.
            writer_r_version: version of R that wrote the file, e.g. "4.3.3".
            min_reader_r_version: minimal version of R needed to read the file.
    """
    parser = MetadataParser()
    _parse(parser, path)
    return parser.metadata


def list_objects(path, encoding=None):
    """
    Read an R RData or Rds file and lists objects and their column names.
    Not all objects are readable, and also it is not always possible to read the column names without parsing the
    whole file, in those cases this method will return Nones instead of column names.

    Parameters
    ----------
        path : str, bytes, Path, or file-like object
            path to the file, or a file-like object with read() and seek() methods (e.g. io.BytesIO).
        encoding : str, optional
            encoding of strings that have no encoding mark in the file, for example "latin1" or "WINDOWS-1252".
            See read_r for details.

    Returns
    -------
        result : list
            a list of dictionaries, where each dictionary has a key "object_name" with the name of the object and
            columns with a list of columns.
    """

    parser = ListObjectsParser()
    if encoding is not None and not isinstance(encoding, str):
        raise PyreadrError("encoding must be a string")
    if encoding:
        parser.set_encoding(encoding)
    _parse(parser, path)
    return parser.object_list
    
    
def write_rdata(path, df, df_name="dataset", dateformat="%Y-%m-%d", datetimeformat="%Y-%m-%d %H:%M:%S", compress=None, compresslevel=9,
                rownames_column=None):
    """
    Write one or more pandas or polars data frames to a RData file.

    Parameters
    ----------
        path : str, bytes, or Path
            path to the file. The string is assumed to be utf-8 encoded.
        df : pandas or polars DataFrame, or dict
            the data frame to write, or a dict (e.g. the OrderedDict returned by read_r) with object names as keys
            and data frames as values, to write several data frames to the same file.
        df_name : str
            name for the R dataframe object, cannot be empty string. If
            not supplied will default to "dataset". Ignored if df is a dict.
        dateformat : str
            string to format datetime.date objects.
            By default "%Y-%m-%d".
        datetimeformat : str
            string to format datetime like objects. By default "%Y-%m-%d %H:%M:%S".
        compress : str, optional
            compression to use, defaults to no compression. Only "gzip" supported.
        compresslevel : int, optional
            compression level for gzip (1-9), default 9.
        rownames_column : str or dict, optional
            name of a column to write as R row names instead of as a regular column. If not set, the index of a
            pandas data frame is written as row names, unless it is the default RangeIndex. Row names are converted
            to strings and cannot contain missing values or duplicates. If df is a dict, a str applies to the data
            frames that have that column, and a dict with object names as keys sets the column per data frame.
    """

    if not isinstance(df, Mapping) and not df_name:
        msg = "df_name must be a valid string"
        raise PyreadrError(msg)

    frames = get_frames_to_write(df, df_name, rownames_column, allow_multiple=True)

    file_format = "rdata"
    writer = PyreadrWriter()

    filename_bytes = _encode_path(path)

    writer.write_r(filename_bytes, file_format, frames, dateformat, datetimeformat, compress, compresslevel)


def write_rds(path, df, dateformat="%Y-%m-%d", datetimeformat="%Y-%m-%d %H:%M:%S", compress=None, compresslevel=9,
              rownames_column=None):
    """
    Write a single pandas or polars data frame to a Rds file.

    Parameters
    ----------
        path : str, bytes, or Path
            path to the file. The string is assumed to be utf-8 encoded.
        df : pandas or polars DataFrame
            the data frame to write.
        dateformat : str
            string to format datetime.date objects.
            By default "%Y-%m-%d".
        datetimeformat : str
            string to format datetime like objects. By default "%Y-%m-%d %H:%M:%S".
        compress : str, optional
            compression to use, defaults to no compression. Only "gzip" supported.
        compresslevel : int, optional
            compression level for gzip (1-9), default 9.
        rownames_column : str, optional
            name of a column to write as R row names instead of as a regular column. If not set, the index of a
            pandas data frame is written as row names, unless it is the default RangeIndex. Row names are converted
            to strings and cannot contain missing values or duplicates.
    """

    df_name = ""   # this is irrelevant in this case, but we need to pass something
    frames = get_frames_to_write(df, df_name, rownames_column, allow_multiple=False)

    file_format = "rds"

    filename_bytes = _encode_path(path)

    writer = PyreadrWriter()
    writer.write_r(filename_bytes, file_format, frames, dateformat, datetimeformat, compress, compresslevel)

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
