
from enum import Enum
import numpy as np
import os.path


class DataType(Enum):
    CHARACTER  = rdata_type_t.RDATA_TYPE_STRING
    INTEGER    = rdata_type_t.RDATA_TYPE_INT32
    NUMERIC    = rdata_type_t.RDATA_TYPE_REAL
    LOGICAL    = rdata_type_t.RDATA_TYPE_LOGICAL
    TIMESTAMP  = rdata_type_t.RDATA_TYPE_TIMESTAMP


cdef int _handle_open(const char *u8_path, void *io_ctx):
    cdef int fd

    path = u8_path.decode('utf-8')
    if not os.path.isfile(path):
        return -1

    IF UNAME_SYSNAME == 'Windows':
        cdef Py_ssize_t length
        u16_path = PyUnicode_AsWideCharString(path, &length)
        fd = _wsopen(u16_path, _O_RDONLY | _O_BINARY, _SH_DENYRD, 0)
        assign_fd(io_ctx, fd)
        return fd
    ELSE:
        return -1


cdef int _handle_table(const char *name, void *ctx):
    parser = <object>ctx
    try:
        Parser.__handle_table(parser, name)
        return rdata_error_t.RDATA_OK
    except Exception as e:
        parser._error = e
        return rdata_error_t.RDATA_ERROR_USER_ABORT


cdef int _handle_column(const char *name, rdata_type_t type, void *data, long count, void *ctx):
    parser = <object>ctx
    try:
        Parser.__handle_column(parser, name, type, data, count)
        return rdata_error_t.RDATA_OK
    except Exception as e:
        parser._error = e
        return rdata_error_t.RDATA_ERROR_USER_ABORT


cdef int _handle_column_name(const char *name, int index, void *ctx):
    parser = <object>ctx
    try:
        Parser.__handle_column_name(parser, name, index)
        return rdata_error_t.RDATA_OK
    except Exception as e:
        parser._error = e
        return rdata_error_t.RDATA_ERROR_USER_ABORT


cdef int _handle_text_value(const char *value, int index, void *ctx):
    parser = <object>ctx
    try:
        Parser.__handle_text_value(parser, value, index)
        return rdata_error_t.RDATA_OK
    except Exception as e:
        parser._error = e
        return rdata_error_t.RDATA_ERROR_USER_ABORT


cdef int _handle_value_label(const char *value, int index, void *ctx):
    parser = <object>ctx
    try:
        Parser.__handle_value_label(parser, value, index)
        return rdata_error_t.RDATA_OK
    except Exception as e:
        parser._error = e
        return rdata_error_t.RDATA_ERROR_USER_ABORT


cdef class Parser:

    cdef rdata_parser_t *_this
    cdef int _row_count
    cdef int _var_count

    cpdef parse(self, path):

        cdef rdata_error_t status

        self._this = rdata_parser_init();
        self._error = None

        IF UNAME_SYSNAME == 'Windows':  # custom file opener for windows *sigh*
            rdata_set_open_handler(self._this, _handle_open)

        rdata_set_table_handler(self._this, _handle_table)
        rdata_set_column_handler(self._this, _handle_column)
        rdata_set_column_name_handler(self._this, _handle_column_name)
        rdata_set_text_value_handler(self._this, _handle_text_value)
        rdata_set_value_label_handler(self._this, _handle_value_label)

        status = rdata_parse(self._this, path.encode('utf-8'), <void*>self)
        rdata_parser_free(self._this)

        if status != RDATA_OK:
            if self._error is not None:
                raise self._error
            else:
                message = rdata_error_message(status).decode('utf-8', 'replace')
                raise ValueError(message)

    def handle_table(self, name):
        pass

    def handle_column(self, name, data_type, data, count):
        pass

    def handle_column_name(self, name, index):
        pass

    def handle_text_value(self, name, index):
        pass

    def handle_value_label(self, name, index):
        pass

    cdef __handle_table(self, const char* name):
        if name == NULL:
            self.handle_table(None)
        else:
            self.handle_table(name.decode('utf-8', 'replace'))

    cdef __handle_column(self, const char *name, rdata_type_t type, void *data, long count):
        cdef double *doubles = <double*>data
        cdef int *ints = <int*>data

        if type == rdata_type_t.RDATA_TYPE_REAL:
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
            new_name = name.decode('utf-8', 'replace')
        data_type = DataType(type)
        self.handle_column(new_name, data_type, array, count)

    cdef __handle_column_name(self, const char *name, int index):
        self.handle_column_name(name.decode('utf-8', 'replace'), index)

    cdef __handle_text_value(self, const char *value, int index):
        if value != NULL:
            self.handle_text_value(value.decode('utf-8', 'replace'), index)
        else:
            self.handle_text_value("", index)

    cdef __handle_value_label(self, const char *value, int index):
        self.handle_value_label(value.decode('utf-8', 'replace'), index)
