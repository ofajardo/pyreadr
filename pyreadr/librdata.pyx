# cython: c_string_type=str, c_string_encoding=utf8, language_level=3

import platform
from enum import Enum
import numpy as np
import pandas as pd
import os.path
from cython.operator cimport dereference as deref
from libc.string cimport strlen

from .custom_errors import PyreadrError, LibrdataError


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
    if platform.system() == 'Windows':
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


cdef int _os_close(int fd) noexcept:
    if platform.system() == 'Windows':
        return _close(fd)
    else:
        return close(fd)


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


cdef class Parser:

    cdef rdata_parser_t *_this
    cdef int _fd
    cdef int _row_count
    cdef int _var_count
    parse_current_table = True

    cpdef parse(self, path) noexcept:

        cdef rdata_error_t status

        self._this = rdata_parser_init();
        self._fd = 0
        self._error = None

        if platform.system() == 'Windows':
            rdata_set_open_handler(self._this, _handle_open)

        rdata_set_table_handler(self._this, _handle_table)
        rdata_set_column_handler(self._this, _handle_column)
        rdata_set_column_name_handler(self._this, _handle_column_name)
        rdata_set_dim_handler(self._this, _handle_dim)
        rdata_set_dim_name_handler(self._this, _handle_dim_name)
        rdata_set_row_name_handler(self._this, _handle_row_name)
        rdata_set_text_value_handler(self._this, _handle_text_value)
        rdata_set_value_label_handler(self._this, _handle_value_label)

        status = rdata_parse(self._this, path, <void*>self)
        #status = rdata_parse(self._this, path.encode('utf-8'), <void*>self)
        rdata_parser_free(self._this)

        if status != RDATA_OK:
            if self._error is not None:
                raise self._error
            else:
                message = rdata_error_message(status)
                raise LibrdataError(message)

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

    def _handle_row_name(self, name, index):
        pass

    def handle_text_value(self, name, index):
        pass

    def handle_value_label(self, name, index):
        pass

    cdef __handle_table(self, const char* name) noexcept:
        if name == NULL:
            self.handle_table(None)
        else:
            self.handle_table(name)

    cdef __handle_column(self, const char *name, rdata_type_t type, void *data, long count) noexcept:
        cdef double *doubles = <double*>data
        cdef int *ints = <int*>data

        if type in [rdata_type_t.RDATA_TYPE_REAL, rdata_type_t.RDATA_TYPE_TIMESTAMP, rdata_type_t.RDATA_TYPE_DATE]:
            array = np.empty([count], dtype=np.float64)
            for i in range(count):
                array[i] = doubles[i];
        elif type == rdata_type_t.RDATA_TYPE_INT32 or type == rdata_type_t.RDATA_TYPE_LOGICAL:
            array = np.empty([count], dtype=np.int32)
            for i in range(count):
                array[i] = ints[i];
        else:
            array = None

        if name == NULL:
            new_name = None
        else:
            new_name = name
        data_type = DataType(type)
        self.handle_column(new_name, data_type, array, count)

    cdef __handle_column_name(self, const char *name, int index) noexcept: 
        self.handle_column_name(name, index)

    cdef __handle_dim(self, const char *name, rdata_type_t datatype, void *data, long count) noexcept:
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

    cdef __handle_dim_name(self, const char *name, int index) noexcept:
        if name == NULL:
            new_name = None
        else:
            new_name = name
        self.handle_dim_name(new_name, index)

    cdef __handle_row_name(self, const char *name, int index) noexcept:
        self.handle_row_name(name, index)

    cdef __handle_text_value(self, const char *value, int index) noexcept:
        if value != NULL:
            self.handle_text_value(value, index)
        else:
            self.handle_text_value(np.nan, index)

    cdef __handle_value_label(self, const char *value, int index) noexcept:
        self.handle_value_label(value, index)


cdef ssize_t _handle_write(const void *data, size_t len, void *ctx) noexcept:
    cdef int fd = deref(<int*>ctx)
    if platform.system() == 'Windows':
        return _write(fd, data, len)
    else:
        return write(fd, data, len)


cdef class Column:
    cdef rdata_column_t *_this

    def add_level_labels(self, labels):
        for label in labels:
            rdata_column_add_factor(self._this, label.encode('utf-8'))


cdef class Writer:

    cdef object _format
    cdef object _row_count
    cdef rdata_writer_t *_writer
    cdef int _fd
    cdef int _current_column_no
    cdef rdata_column_t* _current_column
    cdef bytes _table_name 

    def __init__(self):
        self._format = None
        self._row_count = 0
        self._writer = NULL
        self._fd = 0
        self._current_column_no = -1
        self._current_column = NULL
        self._table_name = b""

    def open(self, path, format):
        cdef rdata_file_format_t fmt;

        if format == 'rds':
            fmt = RDATA_SINGLE_OBJECT
        elif format == 'rdata':
            fmt = RDATA_WORKSPACE
        else:
            raise PyreadrError('Unsupported format')

        self._writer = rdata_writer_init(_handle_write, fmt)
        self._fd = _os_open(path, 'w')

    def set_row_count(self, row_count):
        self._row_count = row_count
        
    def set_table_name(self, name):
        self._table_name = name.encode("utf-8")

    def close(self):
        if self._writer != NULL:
            if self._current_column_no != -1:
                rdata_end_column(self._writer, self._current_column)
            rdata_end_table(self._writer, self._row_count, self._table_name)
            rdata_end_file(self._writer)
            _os_close(self._fd)

    def insert_value(self, row_no, col_no, value, dtype):
        cdef rdata_error_t status;

        if self._current_column_no == -1:
            rdata_begin_file(self._writer, &self._fd)
            rdata_begin_table(self._writer, self._table_name);
            
        if col_no != self._current_column_no:
            if self._current_column_no != -1:
                rdata_end_column(self._writer, self._current_column)
            self._current_column = rdata_get_column(self._writer, col_no)
            rdata_begin_column(self._writer, self._current_column, self._row_count)
            self._current_column_no = col_no

        status = RDATA_OK
        
        if dtype == "NUMERIC":
            status = rdata_append_real_value(self._writer, value)
        elif dtype == "CHARACTER":
            # in the case of character we could also pass NULL as value to become R's NA
            # right now passing an empty string has the same effect
            if pd.isnull(value):
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
        col = Column()
        col._this = column
        return col
        
