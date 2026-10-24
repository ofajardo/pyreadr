# cython: c_string_type=str, c_string_encoding=utf8, language_level=3

import platform
from enum import Enum
import numpy as np
import os.path
from cython.operator cimport dereference as deref
from libc.string cimport strlen, memcpy, memcmp
from libc.stdint cimport int32_t, uint32_t
from libc.stdlib cimport malloc, free

from .custom_errors import PyreadrError, LibrdataError

# checked once: the write callback runs for every value written
cdef bint _is_windows = platform.system() == 'Windows'
# librdata calls the write callback with a few bytes per value, the Writer collects them in a buffer of this size
cdef enum:
    WRITE_BUFFER_SIZE = 1048576


class DataType(Enum):
    CHARACTER  = rdata_type_t.RDATA_TYPE_STRING
    INTEGER    = rdata_type_t.RDATA_TYPE_INT32
    NUMERIC    = rdata_type_t.RDATA_TYPE_REAL
    LOGICAL    = rdata_type_t.RDATA_TYPE_LOGICAL
    TIMESTAMP  = rdata_type_t.RDATA_TYPE_TIMESTAMP
    DATE       = rdata_type_t.RDATA_TYPE_DATE


cdef int _os_open(path, mode) noexcept:
    cdef int flags
    cdef Py_ssize_t length
    if _is_windows:
        if mode == 'r':
            flags = _O_RDONLY | _O_BINARY
            u16_path = PyUnicode_AsWideCharString(path, &length)
            return _wsopen(u16_path, flags, _SH_DENYWR, _S_IREAD | _S_IWRITE)
        else:
            flags = _O_WRONLY | _O_CREAT | _O_BINARY | _O_TRUNC
            u16_path = PyUnicode_AsWideCharString(os.fsdecode(path), &length)
            return _wsopen(u16_path, flags, _SH_DENYRW, _S_IREAD | _S_IWRITE)
    else:
        if mode == 'r':
            flags = O_RDONLY
        else:
            flags = O_WRONLY | O_CREAT | O_TRUNC
        #return open(path.encode('utf-8'), flags, 0644)
        return open(path, flags, 0644)


cdef list _list_with_none(array, missing):
    """
    numpy array to a list (data for polars) with None where missing (boolean array) is True
    """
    values = array.tolist()
    for i in np.flatnonzero(missing).tolist():
        values[i] = None
    return values


cdef int _os_close(int fd) noexcept:
    if _is_windows:
        return _close(fd)
    else:
        return close(fd)


cdef bint _os_write_all(int fd, const char *data, size_t len) noexcept:
    """
    writes len bytes, write may write less than asked. Returns False on error.
    """
    cdef ssize_t written
    while len > 0:
        if _is_windows:
            written = _write(fd, data, len)
        else:
            written = write(fd, data, len)
        if written <= 0:
            return False
        data += written
        len -= written
    return True


cdef int _handle_open(const char* path, void* io_ctx) noexcept:
    cdef rdata_unistd_io_ctx_t* ctx = <rdata_unistd_io_ctx_t*>io_ctx
    cdef int fd
    if not os.path.isfile(path):
        return -1
    fd = _os_open(path, 'r')
    ctx.fd = fd
    return fd

cdef int _handle_table(const char *name, void *ctx) noexcept:
    parser = <Parser>ctx
    try:
        Parser.__handle_table(parser, name)
        return rdata_error_t.RDATA_OK
    except Exception as e:
        parser._error = e
        return rdata_error_t.RDATA_ERROR_USER_ABORT


cdef int _handle_column(const char *name, rdata_type_t type, void *data, long count, void *ctx) noexcept:
    parser = <Parser>ctx
    try:
        if parser.parse_current_table:
            Parser.__handle_column(parser, name, type, data, count)
        return rdata_error_t.RDATA_OK
    except Exception as e:
        parser._error = e
        return rdata_error_t.RDATA_ERROR_USER_ABORT

cdef int _handle_dim(const char *name, rdata_type_t type, void *data, long count, void *ctx) noexcept:
    parser = <Parser>ctx
    try:
        if parser.parse_current_table:
            Parser.__handle_dim(parser, name, type, data, count)
        return rdata_error_t.RDATA_OK
    except Exception as e:
        parser._error = e
        return rdata_error_t.RDATA_ERROR_USER_ABORT


cdef int _handle_column_name(const char *name, int index, void *ctx) noexcept:
    parser = <Parser>ctx
    try:
        Parser.__handle_column_name(parser, name, index)
        return rdata_error_t.RDATA_OK
    except Exception as e:
        parser._error = e
        return rdata_error_t.RDATA_ERROR_USER_ABORT

cdef int _handle_dim_name(const char *name, int index, void *ctx) noexcept:
    parser = <Parser>ctx
    try:
        Parser.__handle_dim_name(parser, name, index)
        return rdata_error_t.RDATA_OK
    except Exception as e:
        parser._error = e
        return rdata_error_t.RDATA_ERROR_USER_ABORT

cdef int _handle_row_name(const char *name, int index, void *ctx) noexcept:
    parser = <Parser>ctx
    try:
        Parser.__handle_row_name(parser, name, index)
        return rdata_error_t.RDATA_OK
    except Exception as e:
        parser._error = e
        return rdata_error_t.RDATA_ERROR_USER_ABORT


cdef int _handle_text_value(const char *value, int index, void *ctx) noexcept:
    parser = <Parser>ctx
    try:
        if parser.parse_current_table:
            Parser.__handle_text_value(parser, value, index)
        return rdata_error_t.RDATA_OK
    except Exception as e:
        parser._error = e
        return rdata_error_t.RDATA_ERROR_USER_ABORT


cdef int _handle_value_label(const char *value, int index, void *ctx) noexcept:
    parser = <Parser>ctx
    try:
        if parser.parse_current_table:
            Parser.__handle_value_label(parser, value, index)
        return rdata_error_t.RDATA_OK
    except Exception as e:
        parser._error = e
        return rdata_error_t.RDATA_ERROR_USER_ABORT


cdef void _handle_error(const char *message, void *ctx) noexcept:
    # detailed error messages from librdata, added to the LibrdataError raised if the parse fails
    parser = <Parser>ctx
    try:
        if message != NULL:
            text = message
            parser._error_messages.append(text.strip())
    except Exception:
        pass


cdef int _handle_header(rdata_compression_t compression, const char *header_line, const rdata_header_t *header,
                        void *ctx) noexcept:
    parser = <Parser>ctx
    try:
        Parser.__handle_header(parser, compression, header_line, header)
        if parser.stop_after_header:
            # nothing else needed: abort the parse, Parser.parse does not raise for this
            parser._stopped_after_header = True
            return 1
        return 0
    except Exception as e:
        parser._error = e
        return 1


cdef str _r_version(uint32_t version):
    # R encodes versions as major * 65536 + minor * 256 + patch
    return "%d.%d.%d" % (version >> 16, (version >> 8) & 255, version & 255)


cdef object _file_object_ctx = None

cdef int _handle_open_file_object(const char *path, void *io_ctx) noexcept:
    return 0

cdef int _handle_close_file_object(void *io_ctx) noexcept:
    return 0

cdef ssize_t _handle_read_file_object(void *buf, size_t nbyte, void *io_ctx) noexcept:
    global _file_object_ctx
    cdef ssize_t bytes_read
    try:
        data = _file_object_ctx.read(nbyte)
        bytes_read = len(data)
        if bytes_read > 0:
            memcpy(buf, <const char*>data, bytes_read)
        return bytes_read
    except:
        return -1

cdef rdata_off_t _handle_seek_file_object(rdata_off_t offset, rdata_io_flags_t whence, void *io_ctx) noexcept:
    global _file_object_ctx
    try:
        if whence == RDATA_SEEK_SET:
            py_whence = 0
        elif whence == RDATA_SEEK_CUR:
            py_whence = 1
        else:
            py_whence = 2
        _file_object_ctx.seek(offset, py_whence)
        return _file_object_ctx.tell()
    except:
        return -1


cdef class Parser:

    cdef rdata_parser_t *_this
    cdef int _fd
    cdef int _row_count
    cdef int _var_count
    parse_current_table = True
    output_format = "pandas"
    encoding = None
    # True to read only the file header (handle_header), see _handle_header
    stop_after_header = False

    def set_encoding(self, encoding):
        self.encoding = encoding

    cpdef parse(self, path, file_object=None):

        global _file_object_ctx
        cdef rdata_error_t status

        self._this = rdata_parser_init();
        self._fd = 0
        self._error = None
        self._error_messages = []
        self._stopped_after_header = False

        # encoding for strings without encoding mark, overrides the one declared in the file
        if self.encoding is not None:
            encoding_bytes = self.encoding.encode('utf-8')
            status = rdata_set_file_character_encoding(self._this, encoding_bytes)
            if status != RDATA_OK:
                rdata_parser_free(self._this)
                raise LibrdataError(rdata_error_message(status))

        if _is_windows:
            rdata_set_open_handler(self._this, _handle_open)

        rdata_set_table_handler(self._this, _handle_table)
        rdata_set_column_handler(self._this, _handle_column)
        rdata_set_column_name_handler(self._this, _handle_column_name)
        rdata_set_dim_handler(self._this, _handle_dim)
        rdata_set_dim_name_handler(self._this, _handle_dim_name)
        rdata_set_row_name_handler(self._this, _handle_row_name)
        rdata_set_text_value_handler(self._this, _handle_text_value)
        rdata_set_value_label_handler(self._this, _handle_value_label)
        rdata_set_error_handler(self._this, _handle_error)
        rdata_set_header_handler(self._this, _handle_header)

        if file_object is not None:
            _file_object_ctx = file_object
            rdata_set_open_handler(self._this, _handle_open_file_object)
            rdata_set_close_handler(self._this, _handle_close_file_object)
            rdata_set_read_handler(self._this, _handle_read_file_object)
            rdata_set_seek_handler(self._this, _handle_seek_file_object)

        status = rdata_parse(self._this, path, <void*>self)
        #status = rdata_parse(self._this, path.encode('utf-8'), <void*>self)
        rdata_parser_free(self._this)

        if status != RDATA_OK:
            if self._error is not None:
                raise self._error
            if status == RDATA_ERROR_USER_ABORT and self._stopped_after_header:
                return
            message = rdata_error_message(status)
            if self._error_messages:
                message = "%s: %s" % (message, "; ".join(self._error_messages))
            raise LibrdataError(message)

    def handle_header(self, metadata):
        """
        metadata: dict with file_type ("RData" or "Rds"), format_version, compression ("gzip", "bzip2", "xz"
        or None), writer_r_version and min_reader_r_version
        """
        pass

    def handle_table(self, name):
        pass

    def handle_column(self, name, data_type, data, count):
        pass

    def handle_column_name(self, name, index):
        pass

    def handle_dim(self, name, data_type, data, count):
        pass

    def handle_dim_name(self, name, index):
        pass

    def handle_row_name(self, name, index):
        pass

    def handle_text_value(self, name, index):
        pass

    def handle_value_label(self, name, index):
        pass

    cdef __handle_header(self, rdata_compression_t compression, const char *header_line,
                         const rdata_header_t *header):
        # RData files start with RDX2 or RDX3, Rds files directly with the serialization format
        file_type = "RData" if memcmp(header_line, b"RDX", 3) == 0 else "Rds"
        if compression == RDATA_COMPRESSION_GZIP:
            compression_name = "gzip"
        elif compression == RDATA_COMPRESSION_BZIP2:
            compression_name = "bzip2"
        elif compression == RDATA_COMPRESSION_LZMA:
            compression_name = "xz"
        else:
            compression_name = None
        self.handle_header({
            "file_type": file_type,
            "format_version": header.format_version,
            "compression": compression_name,
            "writer_r_version": _r_version(header.writer_version),
            "min_reader_r_version": _r_version(header.reader_version),
        })

    cdef __handle_table(self, const char* name):
        if name == NULL:
            self.handle_table(None)
        else:
            self.handle_table(name)

    cdef __handle_column(self, const char *name, rdata_type_t type, void *data, long count):
        cdef double[::1] doubles_view
        cdef int32_t[::1] ints_view

        # copy the whole C array into numpy at once (assigning element by element goes through Python)
        if type in [rdata_type_t.RDATA_TYPE_REAL, rdata_type_t.RDATA_TYPE_TIMESTAMP, rdata_type_t.RDATA_TYPE_DATE]:
            array = np.empty([count], dtype=np.float64)
            if count > 0:
                doubles_view = array
                memcpy(&doubles_view[0], data, count * sizeof(double))
            if self.output_format == "polars":
                if type == rdata_type_t.RDATA_TYPE_REAL:
                    # R's NA is a NaN with 1954 in the low word: null. Any other NaN stays NaN
                    missing = np.isnan(array) & ((array.view(np.uint64) & 0xFFFFFFFF) == 1954)
                else:
                    # dates and timestamps cannot be NaN
                    missing = np.isnan(array)
                array = _list_with_none(array, missing)
        elif type == rdata_type_t.RDATA_TYPE_INT32 or type == rdata_type_t.RDATA_TYPE_LOGICAL:
            array = np.empty([count], dtype=np.int32)
            if count > 0:
                ints_view = array
                memcpy(&ints_view[0], data, count * sizeof(int32_t))
            if self.output_format == "polars":
                array = _list_with_none(array, array <= -2147483648)
        else:
            array = None

        if name == NULL:
            new_name = None
        else:
            new_name = name
        data_type = DataType(type)
        self.handle_column(new_name, data_type, array, count)

    cdef __handle_column_name(self, const char *name, int index):
        # librdata passes NULL for NA names, converting NULL to str would segfault
        if name == NULL:
            new_name = None
        else:
            new_name = name
        self.handle_column_name(new_name, index)

    cdef __handle_dim(self, const char *name, rdata_type_t datatype, void *data, long count):
        cdef int *ints = <int*>data

        data_type = DataType(datatype)
        if datatype == rdata_type_t.RDATA_TYPE_INT32:
            array = np.empty([count], dtype=np.int32)
            for i in range(count):
                array[i] = ints[i];
        else:
            raise PyreadrError('Wrong data type %s for dimensions.' % str(data_type))

        if name == NULL:
            new_name = None
        else:
            new_name = name
        self.handle_dim(new_name, data_type, array, count)

    cdef __handle_dim_name(self, const char *name, int index):
        if name == NULL:
            new_name = None
        else:
            new_name = name
        self.handle_dim_name(new_name, index)

    cdef __handle_row_name(self, const char *name, int index):
        if name == NULL:
            new_name = None
        else:
            new_name = name
        self.handle_row_name(new_name, index)

    cdef __handle_text_value(self, const char *value, int index):
        if value != NULL:
            self.handle_text_value(value, index)
        else:
            if self.output_format == "polars":
                self.handle_text_value(None, index)
            else:
                self.handle_text_value(np.nan, index)

    cdef __handle_value_label(self, const char *value, int index):
        # NULL is a NA factor level (addNA in R)
        if value == NULL:
            new_value = None
        else:
            new_value = value
        self.handle_value_label(new_value, index)


cdef class Column:
    cdef rdata_column_t *_this

    def add_level_labels(self, labels):
        cdef rdata_error_t status
        for label in labels:
            status = rdata_column_add_factor(self._this, label.encode('utf-8'))
            if status != RDATA_OK:
                raise LibrdataError(rdata_error_message(status))


cdef class Writer:
    """
    Writes one or more tables (data frames) to a file: open, then for each table new_table, add_column for all
    its columns, insert_value for all values (column by column) and end_table; finally close. A Rds file holds
    one table.
    """

    cdef rdata_writer_t *_writer
    cdef int _fd
    cdef bint _file_started
    # current table
    cdef bint _table_started
    cdef object _row_count
    cdef bytes _table_name
    cdef object _row_names
    cdef int _column_count
    # librdata numbers the columns of all tables consecutively, index of the first column of the current table
    cdef int _table_first_column
    cdef int _current_column_no
    cdef rdata_column_t* _current_column
    # bytes from librdata's write callback waiting to be written to the file
    cdef char *_buffer
    cdef size_t _buffer_used
    cdef bint _write_failed

    def __cinit__(self):
        self._buffer = NULL

    def __init__(self):
        self._writer = NULL
        self._fd = 0
        self._file_started = False
        self._table_first_column = 0
        self._buffer_used = 0
        self._write_failed = False
        self._reset_table()

    def __dealloc__(self):
        if self._buffer != NULL:
            free(self._buffer)
            self._buffer = NULL

    cdef bint _flush(self) noexcept:
        """
        writes the buffer to the file. Returns False on error.
        """
        if self._buffer_used > 0:
            if not _os_write_all(self._fd, self._buffer, self._buffer_used):
                self._write_failed = True
                return False
            self._buffer_used = 0
        return True

    cdef ssize_t _buffered_write(self, const char *data, size_t len) noexcept:
        """
        called by librdata through _handle_write. Returns len, or -1 on error.
        """
        if self._buffer_used + len > WRITE_BUFFER_SIZE:
            if not self._flush():
                return -1
        if len > WRITE_BUFFER_SIZE:
            if not _os_write_all(self._fd, data, len):
                self._write_failed = True
                return -1
            return len
        memcpy(self._buffer + self._buffer_used, data, len)
        self._buffer_used += len
        return len

    cdef _reset_table(self):
        self._table_started = False
        self._row_count = 0
        self._table_name = b""
        self._row_names = None
        self._column_count = 0
        self._current_column_no = -1
        self._current_column = NULL

    cdef _begin_table(self):
        """
        begins the file (first table only) and the current table. The file has to begin before anything is
        written, as librdata's write callback receives its context (this Writer) there; the table only after all
        its columns were added, as their number is written at the beginning.
        """
        cdef rdata_error_t status = RDATA_OK
        if not self._file_started:
            status = rdata_begin_file(self._writer, <void*>self)
            if status != RDATA_OK:
                raise LibrdataError(rdata_error_message(status))
            self._file_started = True
        status = rdata_begin_table(self._writer, self._table_name)
        if status != RDATA_OK:
            raise LibrdataError(rdata_error_message(status))
        self._table_started = True

    def open(self, path, format):
        cdef rdata_file_format_t fmt;

        if format == 'rds':
            fmt = RDATA_SINGLE_OBJECT
        elif format == 'rdata':
            fmt = RDATA_WORKSPACE
        else:
            raise PyreadrError('Unsupported format')

        if self._buffer == NULL:
            self._buffer = <char*>malloc(WRITE_BUFFER_SIZE)
            if self._buffer == NULL:
                raise MemoryError()
        self._buffer_used = 0
        self._write_failed = False
        self._writer = rdata_writer_init(_handle_write, fmt)
        self._fd = _os_open(path, 'w')

    def new_table(self, name, row_count, row_names=None):
        """
        starts collecting a new table. name: str, row_count: int, row_names: list of str, one per row, or None
        """
        self._reset_table()
        self._table_name = name.encode("utf-8")
        self._row_count = row_count
        self._row_names = row_names

    def end_table(self):
        cdef rdata_error_t status = RDATA_OK
        cdef rdata_column_t* column

        if not self._table_started:
            self._begin_table()
        if self._current_column_no != -1:
            status = rdata_end_column(self._writer, self._current_column)
        else:
            # no values were inserted (zero rows): the columns still have to be written
            for col_no in range(self._column_count):
                column = rdata_get_column(self._writer, self._table_first_column + col_no)
                status = rdata_begin_column(self._writer, column, self._row_count)
                if status == RDATA_OK:
                    status = rdata_end_column(self._writer, column)
                if status != RDATA_OK:
                    break
        if status == RDATA_OK and self._row_names is not None:
            for name in self._row_names:
                status = rdata_append_row_name(self._writer, name.encode('utf-8'))
                if status != RDATA_OK:
                    break
        if status == RDATA_OK:
            status = rdata_end_table(self._writer, self._row_count, self._table_name)
        if status != RDATA_OK:
            raise LibrdataError(rdata_error_message(status))
        self._table_first_column += self._column_count
        self._reset_table()

    def close(self, complete=True):
        """
        ends the file and closes it. complete=False only closes the file, after an error.
        """
        cdef rdata_error_t status = RDATA_OK

        if self._writer != NULL:
            try:
                if complete:
                    if not self._file_started:
                        status = rdata_begin_file(self._writer, <void*>self)
                    if status == RDATA_OK:
                        status = rdata_end_file(self._writer)
                    if status == RDATA_OK and not self._flush():
                        status = RDATA_ERROR_WRITE
            finally:
                _os_close(self._fd)
                rdata_writer_free(self._writer)
                self._writer = NULL
                self._buffer_used = 0
            if status != RDATA_OK:
                raise LibrdataError(rdata_error_message(status))

    def insert_value(self, row_no, col_no, value, dtype):
        """
        col_no: index of the column in the current table
        """
        cdef rdata_error_t status = RDATA_OK

        if not self._table_started:
            self._begin_table()

        if col_no != self._current_column_no:
            if self._current_column_no != -1:
                status = rdata_end_column(self._writer, self._current_column)
            if status == RDATA_OK:
                self._current_column = rdata_get_column(self._writer, self._table_first_column + col_no)
                status = rdata_begin_column(self._writer, self._current_column, self._row_count)
            if status != RDATA_OK:
                raise LibrdataError(rdata_error_message(status))
            self._current_column_no = col_no
        
        if dtype == "NUMERIC":
            status = rdata_append_real_value(self._writer, value)
        elif dtype == "CHARACTER":
            # in the case of character we could also pass NULL as value to become R's NA
            # right now passing an empty string has the same effect
            if value is None or value != value:
                status = rdata_append_string_value(self._writer, NULL)
            else:
                status = rdata_append_string_value(self._writer, value.encode('utf-8'))
        elif dtype == "INTEGER":
            status = rdata_append_int32_value(self._writer, value)
        elif dtype == "LOGICAL":
            status = rdata_append_logical_value(self._writer, value);
        else:
            raise PyreadrError("Unknown data type")
        
        if status != RDATA_OK:
            raise LibrdataError(rdata_error_message(status))
            

    def add_column(self, name, dtype):
        cdef rdata_type_t data_type
        cdef rdata_column_t* column

        if dtype == "NUMERIC":
            data_type = RDATA_TYPE_REAL
        elif dtype == "CHARACTER":
            data_type = RDATA_TYPE_STRING
        elif dtype == "INTEGER":
            data_type = RDATA_TYPE_INT32
        elif dtype == "LOGICAL":
            data_type = RDATA_TYPE_LOGICAL
        else:
            raise PyreadrError("Unknown data type: %s" % dtype)

        column = rdata_add_column(self._writer, name.encode('utf-8'), data_type)
        self._column_count += 1
        col = Column()
        col._this = column
        return col
        


cdef ssize_t _handle_write(const void *data, size_t len, void *ctx) noexcept:
    # ctx is the Writer, see rdata_begin_file in Writer
    cdef Writer writer = <Writer>ctx
    return writer._buffered_write(<const char*>data, len)
