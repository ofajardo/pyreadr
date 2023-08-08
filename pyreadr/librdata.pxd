# cython: c_string_type=str, c_string_encoding=utf8, language_level=3

from libc.time cimport time_t, tm
from libc.stdint cimport int32_t
from libc.stddef cimport wchar_t


cdef extern from '<sys/types.h>':
    ctypedef long off_t

cdef extern from 'Python.h':
    object PyByteArray_FromStringAndSize(const char *string, Py_ssize_t len)

cdef extern from 'libs/librdata/src/rdata.h':

    cdef enum rdata_type_t 'rdata_type_e':
        RDATA_TYPE_STRING
        RDATA_TYPE_INT32
        RDATA_TYPE_REAL
        RDATA_TYPE_LOGICAL
        RDATA_TYPE_TIMESTAMP
        RDATA_TYPE_DATE

    cdef enum rdata_error_t 'rdata_error_e':
        RDATA_OK
        RDATA_ERROR_OPEN
        RDATA_ERROR_SEEK
        RDATA_ERROR_READ
        RDATA_ERROR_MALLOC
        RDATA_ERROR_USER_ABORT
        RDATA_ERROR_PARSE
        RDATA_ERROR_WRITE
        RDATA_ERROR_FACTOR
        RDATA_ERROR_UNSUPPORTED_COMPRESSION

    cdef enum rdata_file_format_s 'rdata_file_format_t':
        RDATA_WORKSPACE
        RDATA_SINGLE_OBJECT
    ctypedef rdata_file_format_s rdata_file_format_t

    const char *rdata_error_message(rdata_error_t error_code);

    ctypedef int (*rdata_column_handler)(const char *name, rdata_type_t type,
            void *data, long count, void *ctx);
    ctypedef int (*rdata_table_handler)(const char *name, void *ctx);
    ctypedef int (*rdata_text_value_handler)(const char *value, int index, void *ctx);
    ctypedef int (*rdata_column_name_handler)(const char *value, int index, void *ctx);
    ctypedef void (*rdata_error_handler)(const char *error_message, void *ctx);
    ctypedef int (*rdata_progress_handler)(double progress, void *ctx);

    #IF UNAME_SYSNAME == 'Windows':
    #    ctypedef _off64_t rdata_off_t;
    #ELSE:
    ctypedef off_t rdata_off_t;

    cdef enum rdata_io_flags_e 'rdata_io_flags_e':
        RDATA_SEEK_SET
        RDATA_SEEK_CUR
        RDATA_SEEK_END
    ctypedef rdata_io_flags_e rdata_io_flags_t

    ctypedef int (*rdata_open_handler)(const char *path, void *io_ctx);
    ctypedef int (*rdata_close_handler)(void *io_ctx);
    ctypedef rdata_off_t (*rdata_seek_handler)(rdata_off_t offset, rdata_io_flags_t whence, void *io_ctx);
    ctypedef ssize_t (*rdata_read_handler)(void *buf, size_t nbyte, void *io_ctx);
    ctypedef rdata_error_t (*rdata_update_handler)(long file_size, rdata_progress_handler progress_handler, void *user_ctx, void *io_ctx);

    cdef struct rdata_io_t 'rdata_io_s':
        pass

    cdef struct rdata_parser_t 'rdata_parser_s':
        pass

    rdata_parser_t *rdata_parser_init();
    void rdata_parser_free(rdata_parser_t *parser);

    rdata_error_t rdata_set_table_handler(rdata_parser_t *parser, rdata_table_handler table_handler);
    rdata_error_t rdata_set_column_handler(rdata_parser_t *parser, rdata_column_handler column_handler);
    rdata_error_t rdata_set_column_name_handler(rdata_parser_t *parser, rdata_column_name_handler column_name_handler);
    rdata_error_t rdata_set_row_name_handler(rdata_parser_t *parser, rdata_column_name_handler row_name_handler);
    rdata_error_t rdata_set_text_value_handler(rdata_parser_t *parser, rdata_text_value_handler text_value_handler);
    rdata_error_t rdata_set_value_label_handler(rdata_parser_t *parser, rdata_text_value_handler value_label_handler);
    rdata_error_t rdata_set_dim_handler(rdata_parser_t *parser, rdata_column_handler dim_handler);
    rdata_error_t rdata_set_dim_name_handler(rdata_parser_t *parser, rdata_text_value_handler dim_name_handler);
    rdata_error_t rdata_set_error_handler(rdata_parser_t *parser, rdata_error_handler error_handler);
    rdata_error_t rdata_set_open_handler(rdata_parser_t *parser, rdata_open_handler open_handler);
    rdata_error_t rdata_set_close_handler(rdata_parser_t *parser, rdata_close_handler close_handler);
    rdata_error_t rdata_set_seek_handler(rdata_parser_t *parser, rdata_seek_handler seek_handler);
    rdata_error_t rdata_set_read_handler(rdata_parser_t *parser, rdata_read_handler read_handler);
    rdata_error_t rdata_set_update_handler(rdata_parser_t *parser, rdata_update_handler update_handler);
    rdata_error_t rdata_set_io_ctx(rdata_parser_t *parser, void *io_ctx);
    # /* rdata_parse works on RData and RDS. The table handler will be called once
    #  * per data frame in RData files, and zero times on RDS files. */
    rdata_error_t rdata_parse(rdata_parser_t *parser, const char *filename, void *user_ctx);


    # // Write API
    ctypedef ssize_t (*rdata_data_writer)(const void *data, size_t len, void *ctx);

    cdef struct rdata_column_t 'rdata_column_s':
        pass

    cdef struct rdata_writer_t 'rdata_writer_s':
        pass

    rdata_writer_t *rdata_writer_init(rdata_data_writer write_callback, rdata_file_format_t format);
    void rdata_writer_free(rdata_writer_t *writer);

    rdata_column_t *rdata_add_column(rdata_writer_t *writer, const char *name, rdata_type_t type);

    rdata_error_t rdata_column_set_label(rdata_column_t *column, const char *label);
    rdata_error_t rdata_column_add_factor(rdata_column_t *column, const char *factor);

    rdata_column_t *rdata_get_column(rdata_writer_t *writer, int32_t j);

    rdata_error_t rdata_begin_file(rdata_writer_t *writer, void *ctx);
    rdata_error_t rdata_begin_table(rdata_writer_t *writer, const char *variable_name);
    rdata_error_t rdata_begin_column(rdata_writer_t *writer, rdata_column_t *column, int32_t row_count);

    rdata_error_t rdata_append_real_value(rdata_writer_t *writer, double value);
    rdata_error_t rdata_append_int32_value(rdata_writer_t *writer, int32_t value);
    rdata_error_t rdata_append_timestamp_value(rdata_writer_t *writer, time_t value);
    rdata_error_t rdata_append_date_value(rdata_writer_t *writer, tm *value)
    rdata_error_t rdata_append_logical_value(rdata_writer_t *writer, int value);
    rdata_error_t rdata_append_string_value(rdata_writer_t *writer, const char *value);

    rdata_error_t rdata_end_column(rdata_writer_t *writer, rdata_column_t *column);
    rdata_error_t rdata_end_table(rdata_writer_t *writer, int32_t row_count, const char *datalabel);
    rdata_error_t rdata_end_file(rdata_writer_t *writer);

cdef extern from 'libs/librdata/src/rdata_io_unistd.h':
    cdef struct rdata_unistd_io_ctx_t 'rdata_unistd_io_ctx_s':
        int fd

cdef extern from "conditional_includes.h":
    wchar_t* PyUnicode_AsWideCharString(object, Py_ssize_t *) except NULL
    int _wsopen(const wchar_t *filename, int oflag, int shflag, int pmode)
    int _O_RDONLY
    int _O_BINARY
    int _O_WRONLY
    int _O_CREAT
    int _O_TRUNC
    int _SH_DENYRW  # Denies read and write access to a file.
    int _SH_DENYWR  # Denies write access to a file.
    int _SH_DENYRD  # Denies read access to a file.
    int _SH_DENYNO
    void assign_fd(void *io_ctx, int fd)
    int _close(int fd)
    ssize_t _write(int fd, const void *buf, size_t nbyte)
    int _S_IREAD
    int _S_IWRITE
    int open(const char *path, int oflag, int mode)
    int close(int fd)
    ssize_t write(int fd, const void *buf, size_t nbyte)
    int O_WRONLY
    int O_RDONLY
    int O_CREAT
    int O_TRUNC

#IF UNAME_SYSNAME == 'Windows':

    #cdef extern from 'Python.h':
        #wchar_t* PyUnicode_AsWideCharString(object, Py_ssize_t *) except NULL

    #cdef extern from '<fcntl.h>':
        #int _wsopen(const wchar_t *filename, int oflag, int shflag, int pmode)
        #cdef int _O_RDONLY
        #cdef int _O_BINARY
        #cdef int _O_CREAT
        #cdef int _O_WRONLY
        #cdef int _O_TRUNC

    #cdef extern from '<io.h>':
        #cdef int _close(int fd)
        #ssize_t _write(int fd, const void *buf, size_t nbyte)

    #cdef extern from '<share.h>':
        #cdef int _SH_DENYRW  # Denies read and write access to a file.
        #cdef int _SH_DENYWR  # Denies write access to a file.
        #cdef int _SH_DENYRD  # Denies read access to a file.
        #cdef int _SH_DENYNO

    #cdef extern from '<sys/stat.h>':
        #cdef int _S_IREAD
        #cdef int _S_IWRITE

#ELSE:
    #cdef extern from '<sys/stat.h>':
        #int open(const char *path, int oflag, int mode)

    #cdef extern from '<unistd.h>':
        #int close(int fd)
	#ssize_t write(int fd, const void *buf, size_t nbyte)

    #cdef extern from '<fcntl.h>':
        #cdef int O_WRONLY
        #cdef int O_RDONLY
        #cdef int O_CREAT
        #cdef int O_TRUNC
