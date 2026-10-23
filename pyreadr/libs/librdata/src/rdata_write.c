
#include <stdlib.h>
#include <string.h>
#include <time.h>

#if HAVE_ZLIB
#include <zlib.h>
#endif

#include "CKHashTable.h"
#include "rdata.h"
#include "rdata_internal.h"

#define R_TAG           0x01
#define R_OBJECT        0x02
#define R_ATTRIBUTES    0x04

#define INITIAL_COLUMNS_CAPACITY    100
#define INITIAL_ROW_NAMES_CAPACITY  100

#define GZIP_BUFFER_SIZE    65536

#ifdef _WIN32
#define timegm _mkgmtime
#endif

#if HAVE_ZLIB
typedef struct rdata_gzip_ctx_s {
    z_stream        strm;
    unsigned char   buffer[GZIP_BUFFER_SIZE];
} rdata_gzip_ctx_t;
#endif

rdata_writer_t *rdata_writer_init(rdata_data_writer write_callback, rdata_file_format_t format) {
    rdata_writer_t *writer = calloc(1, sizeof(rdata_writer_t));
    writer->file_format = format;
    writer->bswap = machine_is_little_endian();
    writer->atom_table = ck_hash_table_init(100, 24);
    writer->data_writer = write_callback;

    writer->columns_capacity = INITIAL_COLUMNS_CAPACITY;
    writer->columns = malloc(writer->columns_capacity * sizeof(rdata_column_t *));

    return writer;
}

static void rdata_writer_free_row_names(rdata_writer_t *writer) {
    int i;
    for (i=0; i<writer->row_names_count; i++) {
        free(writer->row_names[i]);
    }
    writer->row_names_count = 0;
}

static void rdata_writer_free_compression(rdata_writer_t *writer) {
#if HAVE_ZLIB
    if (writer->compression_ctx) {
        rdata_gzip_ctx_t *gzip = (rdata_gzip_ctx_t *)writer->compression_ctx;
        deflateEnd(&gzip->strm);
        free(gzip);
        writer->compression_ctx = NULL;
    }
#endif
}

void rdata_writer_free(rdata_writer_t *writer) {
    ck_hash_table_free(writer->atom_table);
    int i, j;
    for (i=0; i<writer->columns_count; i++) {
        rdata_column_t *column = writer->columns[i];
        for (j=0; j<column->factor_count; j++) {
            free(column->factor[j]);
        }
        free(column->factor);
        free(column);
    }
    free(writer->columns);
    rdata_writer_free_row_names(writer);
    free(writer->row_names);
    rdata_writer_free_compression(writer);
    free(writer);
}

rdata_error_t rdata_writer_set_compression(rdata_writer_t *writer, rdata_compression_t compression) {
    if (compression == RDATA_COMPRESSION_NONE) {
        writer->compression = compression;
        return RDATA_OK;
    }
#if HAVE_ZLIB
    if (compression == RDATA_COMPRESSION_GZIP) {
        writer->compression = compression;
        return RDATA_OK;
    }
#endif
    return RDATA_ERROR_UNSUPPORTED_COMPRESSION;
}

rdata_column_t *rdata_add_column(rdata_writer_t *writer, const char *name, rdata_type_t type) {
    if (writer->columns_count == writer->columns_capacity) {
        writer->columns_capacity *= 2;
        writer->columns = realloc(writer->columns,
                writer->columns_capacity * sizeof(rdata_column_t *));
    }
    rdata_column_t *new_column = calloc(1, sizeof(rdata_column_t));

    new_column->index = writer->columns_count++;

    writer->columns[new_column->index] = new_column;

    new_column->type = type;

    if (name) {
        snprintf(new_column->name, sizeof(new_column->name), "%s", name);
    }

    return new_column;
}

rdata_column_t *rdata_get_column(rdata_writer_t *writer, int32_t j) {
    return writer->columns[j];
}

rdata_error_t rdata_column_set_label(rdata_column_t *column, const char *label) {
    snprintf(column->label, sizeof(column->label), "%s", label);
    return RDATA_OK;
}

rdata_error_t rdata_column_add_factor(rdata_column_t *column, const char *factor) {
    if (column->type != RDATA_TYPE_INT32)
        return RDATA_ERROR_FACTOR;

    char *factor_copy = malloc(strlen(factor)+1);
    strcpy(factor_copy, factor);

    column->factor_count++;
    column->factor = realloc(column->factor, sizeof(char *) * column->factor_count);
    column->factor[column->factor_count-1] = factor_copy;

    return RDATA_OK;
}

rdata_error_t rdata_append_row_name(rdata_writer_t *writer, const char *name) {
    if (writer->row_names_count == writer->row_names_capacity) {
        int32_t new_capacity = writer->row_names_capacity ? 2 * writer->row_names_capacity : INITIAL_ROW_NAMES_CAPACITY;
        char **new_row_names = realloc(writer->row_names, new_capacity * sizeof(char *));
        if (new_row_names == NULL)
            return RDATA_ERROR_MALLOC;
        writer->row_names = new_row_names;
        writer->row_names_capacity = new_capacity;
    }

    char *name_copy = NULL;
    if (name) {
        name_copy = malloc(strlen(name)+1);
        if (name_copy == NULL)
            return RDATA_ERROR_MALLOC;
        strcpy(name_copy, name);
    }

    writer->row_names[writer->row_names_count++] = name_copy;

    return RDATA_OK;
}

static rdata_error_t rdata_write_raw_bytes(rdata_writer_t *writer, const void *data, size_t len) {
    if (len == 0)
        return RDATA_OK;

    ssize_t bytes_written = writer->data_writer(data, len, writer->user_ctx);
    if (bytes_written < 0 || (size_t)bytes_written < len) {
        return RDATA_ERROR_WRITE;
    }
    writer->bytes_written += bytes_written;
    return RDATA_OK;
}

#if HAVE_ZLIB
static rdata_error_t rdata_gzip_write(rdata_writer_t *writer, const void *data, size_t len, int flush) {
    rdata_gzip_ctx_t *gzip = (rdata_gzip_ctx_t *)writer->compression_ctx;
    rdata_error_t retval = RDATA_OK;

    gzip->strm.next_in = (Bytef *)data;
    gzip->strm.avail_in = len;

    do {
        gzip->strm.next_out = gzip->buffer;
        gzip->strm.avail_out = sizeof(gzip->buffer);

        int result = deflate(&gzip->strm, flush);
        if (result == Z_STREAM_ERROR) {
            retval = RDATA_ERROR_WRITE;
            goto cleanup;
        }

        size_t have = sizeof(gzip->buffer) - gzip->strm.avail_out;
        if ((retval = rdata_write_raw_bytes(writer, gzip->buffer, have)) != RDATA_OK)
            goto cleanup;
    } while (gzip->strm.avail_out == 0);

cleanup:
    return retval;
}
#endif

static rdata_error_t rdata_write_bytes(rdata_writer_t *writer, const void *data, size_t len) {
#if HAVE_ZLIB
    if (writer->compression_ctx) {
        return rdata_gzip_write(writer, data, len, Z_NO_FLUSH);
    }
#endif
    return rdata_write_raw_bytes(writer, data, len);
}

static rdata_error_t rdata_write_integer(rdata_writer_t *writer, int32_t val) {
    if (writer->bswap) {
        val = byteswap4(val);
    }
    return rdata_write_bytes(writer, &val, sizeof(val));
}

static rdata_error_t rdata_write_double(rdata_writer_t *writer, double val) {
    if (writer->bswap) {
        val = byteswap_double(val);
    }
    return rdata_write_bytes(writer, &val, sizeof(val));
}

static rdata_error_t rdata_write_header_with_levels(rdata_writer_t *writer, int type, int flags, unsigned int levels) {
    rdata_sexptype_header_t header;
    memset(&header, 0, sizeof(header));

    header.type = type;
    header.object = !!(flags & R_OBJECT);
    header.tag = !!(flags & R_TAG);
    header.attributes = !!(flags & R_ATTRIBUTES);
    header.gp = levels;

    uint32_t sexp_int;

    memcpy(&sexp_int, &header, sizeof(header));

    return rdata_write_integer(writer, sexp_int);
}

static rdata_error_t rdata_write_header(rdata_writer_t *writer, int type, int flags) {
    return rdata_write_header_with_levels(writer, type, flags, 0);
}

static rdata_error_t rdata_write_string(rdata_writer_t *writer, const char *string) {
    rdata_error_t retval = RDATA_OK;
    ssize_t len = -1;
    unsigned int levels = 0;

    if (string) {
        len = strlen(string);
        /* Strings are expected to be UTF-8. Flag them as such so that R does
         * not misinterpret them in a non-UTF-8 locale (e.g. on Windows). */
        levels = RDATA_CHARSXP_ASCII;
        ssize_t i;
        for (i=0; i<len; i++) {
            if ((unsigned char)string[i] & 0x80) {
                levels = RDATA_CHARSXP_UTF8;
                break;
            }
        }
    }

    retval = rdata_write_header_with_levels(writer, RDATA_SEXPTYPE_CHARACTER_STRING, 0, levels);
    if (retval != RDATA_OK)
        goto cleanup;

    retval = rdata_write_integer(writer, len);
    if (retval != RDATA_OK)
        goto cleanup;

    if (len > 0)
        return rdata_write_bytes(writer, string, len);

cleanup:
    return retval;
}

static rdata_error_t rdata_write_pairlist_key(rdata_writer_t *writer, const char *key) {
    rdata_error_t retval = RDATA_OK;
    ck_hash_table_t *atom_table = (ck_hash_table_t *)writer->atom_table;
    uint64_t ref = (uint64_t)ck_str_hash_lookup(key, atom_table);
    if (ref == 0) {
        ck_str_hash_insert(key, (void *)(atom_table->count + 1), atom_table);

        retval = rdata_write_integer(writer, 1);
        if (retval != RDATA_OK)
            goto cleanup;

        retval = rdata_write_string(writer, key);
    } else {
        retval = rdata_write_integer(writer, (ref << 8) | 0xFF);
    }

cleanup:
    return retval;
}

static rdata_error_t rdata_write_pairlist_header(rdata_writer_t *writer, const char *key) {
    rdata_error_t retval = RDATA_OK;

    retval = rdata_write_header(writer, RDATA_SEXPTYPE_PAIRLIST, R_TAG);
    if (retval != RDATA_OK)
        goto cleanup;

    retval = rdata_write_pairlist_key(writer, key);
    if (retval != RDATA_OK)
        goto cleanup;

cleanup:
    return retval;
}

static rdata_error_t rdata_write_attributed_vector_header(rdata_writer_t *writer, int type, int32_t size) {
    rdata_error_t retval = RDATA_OK;

    retval = rdata_write_header(writer, type, R_OBJECT | R_ATTRIBUTES);
    if (retval != RDATA_OK)
        goto cleanup;

    retval = rdata_write_integer(writer, size);
    if (retval != RDATA_OK)
        goto cleanup;

cleanup:
    return retval;
}

static rdata_error_t rdata_write_simple_vector_header(rdata_writer_t *writer, int type, int32_t size) {
    rdata_error_t retval = RDATA_OK;

    retval = rdata_write_header(writer, type, 0);
    if (retval != RDATA_OK)
        goto cleanup;

    retval = rdata_write_integer(writer, size);
    if (retval != RDATA_OK)
        goto cleanup;

cleanup:
    return retval;
}

static rdata_error_t rdata_write_class_pairlist(rdata_writer_t *writer, const char *class) {
    rdata_error_t retval = RDATA_OK;

    retval = rdata_write_pairlist_header(writer, "class");
    if (retval != RDATA_OK)
        goto cleanup;

    retval = rdata_write_simple_vector_header(writer, RDATA_SEXPTYPE_CHARACTER_VECTOR, 1);
    if (retval != RDATA_OK)
        goto cleanup;

    retval = rdata_write_string(writer, class);
    if (retval != RDATA_OK)
        goto cleanup;

cleanup:
    return retval;
}

rdata_error_t rdata_begin_file(rdata_writer_t *writer, void *user_ctx) {
    rdata_error_t retval = RDATA_OK;

    writer->user_ctx = user_ctx;

    if (writer->compression == RDATA_COMPRESSION_GZIP) {
#if HAVE_ZLIB
        rdata_gzip_ctx_t *gzip = calloc(1, sizeof(rdata_gzip_ctx_t));
        if (gzip == NULL) {
            retval = RDATA_ERROR_MALLOC;
            goto cleanup;
        }
        /* windowBits 15 + 16 selects the gzip wrapper, which is what R writes */
        if (deflateInit2(&gzip->strm, Z_DEFAULT_COMPRESSION, Z_DEFLATED, 15 + 16, 8, Z_DEFAULT_STRATEGY) != Z_OK) {
            free(gzip);
            retval = RDATA_ERROR_MALLOC;
            goto cleanup;
        }
        writer->compression_ctx = gzip;
#else
        retval = RDATA_ERROR_UNSUPPORTED_COMPRESSION;
        goto cleanup;
#endif
    } else if (writer->compression != RDATA_COMPRESSION_NONE) {
        retval = RDATA_ERROR_UNSUPPORTED_COMPRESSION;
        goto cleanup;
    }

    if (writer->file_format == RDATA_WORKSPACE) {
        retval = rdata_write_bytes(writer, "RDX2\n", 5);
        if (retval != RDATA_OK)
            goto cleanup;
    }

    rdata_header_t v2_header;
    memcpy(v2_header.header, "X\n", sizeof("X\n")-1);
    v2_header.format_version = 2;
    v2_header.reader_version = 131840;
    v2_header.writer_version = 131840;

    if (writer->bswap) {
        v2_header.format_version = byteswap4(v2_header.format_version);
        v2_header.reader_version = byteswap4(v2_header.reader_version);
        v2_header.writer_version = byteswap4(v2_header.writer_version);
    }

    retval = rdata_write_bytes(writer, &v2_header, sizeof(v2_header));
    if (retval != RDATA_OK)
        goto cleanup;

cleanup:
    return retval;
}

static int32_t rdata_table_columns_count(rdata_writer_t *writer) {
    return writer->columns_count - writer->table_first_column;
}

rdata_error_t rdata_begin_table(rdata_writer_t *writer, const char *variable_name) {
    rdata_error_t retval = RDATA_OK;

    writer->table_columns_written = 0;

    if (writer->file_format == RDATA_WORKSPACE) {
        retval = rdata_write_pairlist_header(writer, variable_name);
        if (retval != RDATA_OK)
            goto cleanup;
    }

    retval = rdata_write_attributed_vector_header(writer, RDATA_SEXPTYPE_GENERIC_VECTOR,
            rdata_table_columns_count(writer));
    if (retval != RDATA_OK)
        goto cleanup;

cleanup:
    return retval;
}

static rdata_error_t rdata_begin_factor_column(rdata_writer_t *writer, rdata_column_t *column, int32_t row_count) {
    return rdata_write_attributed_vector_header(writer, RDATA_SEXPTYPE_INTEGER_VECTOR, row_count);
}

static rdata_error_t rdata_end_factor_column(rdata_writer_t *writer, rdata_column_t *column) {
    int i;

    rdata_error_t retval = RDATA_OK;

    retval = rdata_write_pairlist_header(writer, "levels");
    if (retval != RDATA_OK)
        goto cleanup;

    retval = rdata_write_simple_vector_header(writer,
            RDATA_SEXPTYPE_CHARACTER_VECTOR, column->factor_count);
    if (retval != RDATA_OK)
        goto cleanup;

    for (i=0; i<column->factor_count; i++) {
        retval = rdata_write_string(writer, column->factor[i]);
        if (retval != RDATA_OK)
            goto cleanup;
    }

    retval = rdata_write_class_pairlist(writer, "factor");
    if (retval != RDATA_OK)
        goto cleanup;

    retval = rdata_write_header(writer, RDATA_PSEUDO_SXP_NIL, 0);
    if (retval != RDATA_OK)
        goto cleanup;

cleanup:
    return retval;
}

static rdata_error_t rdata_begin_real_column(rdata_writer_t *writer,rdata_column_t *column, int32_t row_count) {
    return rdata_write_simple_vector_header(writer, RDATA_SEXPTYPE_REAL_VECTOR, row_count);
}

static rdata_error_t rdata_end_real_column(rdata_writer_t *writer, rdata_column_t *column) {
    return RDATA_OK;
}

static rdata_error_t rdata_begin_timestamp_column(rdata_writer_t *writer, rdata_column_t *column, int32_t row_count) {
    return rdata_write_attributed_vector_header(writer, RDATA_SEXPTYPE_REAL_VECTOR, row_count);
}

static rdata_error_t rdata_end_timestamp_column(rdata_writer_t *writer, rdata_column_t *column) {
    rdata_error_t retval = RDATA_OK;

    retval = rdata_write_class_pairlist(writer, "POSIXct");
    if (retval != RDATA_OK)
        goto cleanup;

    retval = rdata_write_header(writer, RDATA_PSEUDO_SXP_NIL, 0);
    if (retval != RDATA_OK)
        goto cleanup;

cleanup:
    return retval;
}

static rdata_error_t rdata_begin_date_column(rdata_writer_t *writer, rdata_column_t *column, int32_t row_count) {
    return rdata_write_attributed_vector_header(writer, RDATA_SEXPTYPE_REAL_VECTOR, row_count);
}

static rdata_error_t rdata_end_date_column(rdata_writer_t *writer, rdata_column_t *column) {
    rdata_error_t retval = RDATA_OK;

    retval = rdata_write_class_pairlist(writer, "Date");
    if (retval != RDATA_OK)
        goto cleanup;

    retval = rdata_write_header(writer, RDATA_PSEUDO_SXP_NIL, 0);
    if (retval != RDATA_OK)
        goto cleanup;

cleanup:
    return retval;
}

static rdata_error_t rdata_begin_integer_column(rdata_writer_t *writer, rdata_column_t *column, int32_t row_count) {
    return rdata_write_simple_vector_header(writer, RDATA_SEXPTYPE_INTEGER_VECTOR, row_count);
}

static rdata_error_t rdata_end_integer_column(rdata_writer_t *writer, rdata_column_t *column) {
    return RDATA_OK;
}

static rdata_error_t rdata_begin_logical_column(rdata_writer_t *writer, rdata_column_t *column, int32_t row_count) {
    return rdata_write_simple_vector_header(writer, RDATA_SEXPTYPE_LOGICAL_VECTOR, row_count);
}

static rdata_error_t rdata_end_logical_column(rdata_writer_t *writer, rdata_column_t *column) {
    return RDATA_OK;
}

static rdata_error_t rdata_begin_string_column(rdata_writer_t *writer, rdata_column_t *column, int32_t row_count) {
    return rdata_write_simple_vector_header(writer, RDATA_SEXPTYPE_CHARACTER_VECTOR, row_count);
}

static rdata_error_t rdata_end_string_column(rdata_writer_t *writer, rdata_column_t *column) {
    return RDATA_OK;
}

rdata_error_t rdata_begin_column(rdata_writer_t *writer, rdata_column_t *column, int32_t row_count) {
    rdata_type_t type = column->type;

    /* Columns must be written in the order they were added, and must belong
     * to the current table; otherwise the "names" attribute written by
     * rdata_end_table would not line up with the data. */
    if (column->index != writer->table_first_column + writer->table_columns_written)
        return RDATA_ERROR_COLUMN_MISMATCH;

    writer->table_columns_written++;

    if (type == RDATA_TYPE_INT32) {
        if (column->factor_count)
            return rdata_begin_factor_column(writer, column, row_count);
        return rdata_begin_integer_column(writer, column, row_count);
    }
    if (type == RDATA_TYPE_REAL)
        return rdata_begin_real_column(writer, column, row_count);
    if (type == RDATA_TYPE_TIMESTAMP)
        return rdata_begin_timestamp_column(writer, column, row_count);
    if (type == RDATA_TYPE_DATE)
        return rdata_begin_date_column(writer, column, row_count);
    if (type == RDATA_TYPE_LOGICAL)
        return rdata_begin_logical_column(writer, column, row_count);
    if (type == RDATA_TYPE_STRING)
        return rdata_begin_string_column(writer, column, row_count);

    return RDATA_OK;
}

rdata_error_t rdata_append_real_value(rdata_writer_t *writer, double value) {
    return rdata_write_double(writer, value);
}

rdata_error_t rdata_append_int32_value(rdata_writer_t *writer, int32_t value) {
    return rdata_write_integer(writer, value);
}

rdata_error_t rdata_append_timestamp_value(rdata_writer_t *writer, time_t value) {
    return rdata_write_double(writer, value);
}

rdata_error_t rdata_append_date_value(rdata_writer_t *writer, struct tm *value) {
    return rdata_write_double(writer, timegm(value) / 86400);
}

rdata_error_t rdata_append_logical_value(rdata_writer_t *writer, int value) {
    if (value < 0)
        return rdata_write_integer(writer, INT32_MIN);

    return rdata_write_integer(writer, (value > 0));
}

rdata_error_t rdata_append_string_value(rdata_writer_t *writer, const char *value) {
    return rdata_write_string(writer, value);
}

rdata_error_t rdata_end_column(rdata_writer_t *writer, rdata_column_t *column) {
    rdata_type_t type = column->type;

    if (type == RDATA_TYPE_INT32) {
        if (column->factor_count)
            return rdata_end_factor_column(writer, column);
        return rdata_end_integer_column(writer, column);
    }
    if (type == RDATA_TYPE_REAL)
        return rdata_end_real_column(writer, column);
    if (type == RDATA_TYPE_TIMESTAMP)
        return rdata_end_timestamp_column(writer, column);
    if (type == RDATA_TYPE_DATE)
        return rdata_end_date_column(writer, column);
    if (type == RDATA_TYPE_LOGICAL)
        return rdata_end_logical_column(writer, column);
    if (type == RDATA_TYPE_STRING)
        return rdata_end_string_column(writer, column);

    return RDATA_OK;
}

rdata_error_t rdata_end_table(rdata_writer_t *writer, int32_t row_count, const char *datalabel) {
    int i;
    rdata_error_t retval = RDATA_OK;
    int32_t table_columns_count = rdata_table_columns_count(writer);
    rdata_column_t **table_columns = writer->columns + writer->table_first_column;

    if (writer->table_columns_written != table_columns_count) {
        retval = RDATA_ERROR_COLUMN_MISMATCH;
        goto cleanup;
    }

    if (writer->row_names_count > 0 && writer->row_names_count != row_count) {
        retval = RDATA_ERROR_ROW_NAME_COUNT;
        goto cleanup;
    }

    retval = rdata_write_pairlist_header(writer, "datalabel");
    if (retval != RDATA_OK)
        goto cleanup;

    retval = rdata_write_simple_vector_header(writer, RDATA_SEXPTYPE_CHARACTER_VECTOR, 1);
    if (retval != RDATA_OK)
        goto cleanup;

    retval = rdata_write_string(writer, datalabel);
    if (retval != RDATA_OK)
        goto cleanup;

    retval = rdata_write_pairlist_header(writer, "names");
    if (retval != RDATA_OK)
        goto cleanup;

    retval = rdata_write_simple_vector_header(writer,
            RDATA_SEXPTYPE_CHARACTER_VECTOR, table_columns_count);
    if (retval != RDATA_OK)
        goto cleanup;

    for (i=0; i<table_columns_count; i++) {
        retval = rdata_write_string(writer, table_columns[i]->name);
        if (retval != RDATA_OK)
            goto cleanup;
    }

    retval = rdata_write_pairlist_header(writer, "var.labels");
    if (retval != RDATA_OK)
        goto cleanup;

    retval = rdata_write_simple_vector_header(writer,
            RDATA_SEXPTYPE_CHARACTER_VECTOR, table_columns_count);
    if (retval != RDATA_OK)
        goto cleanup;

    for (i=0; i<table_columns_count; i++) {
        retval = rdata_write_string(writer, table_columns[i]->label);
        if (retval != RDATA_OK)
            goto cleanup;
    }

    retval = rdata_write_class_pairlist(writer, "data.frame");
    if (retval != RDATA_OK)
        goto cleanup;

    if (row_count > 0) {
        retval = rdata_write_pairlist_header(writer, "row.names");
        if (retval != RDATA_OK)
            goto cleanup;

        retval = rdata_write_simple_vector_header(writer,
                RDATA_SEXPTYPE_CHARACTER_VECTOR, row_count);
        if (retval != RDATA_OK)
            goto cleanup;

        char buf[128];
        for (i=0; i<row_count; i++) {
            const char *row_name = NULL;
            if (writer->row_names_count > 0) {
                row_name = writer->row_names[i];
            } else {
                snprintf(buf, sizeof(buf), "%d", i+1);
                row_name = buf;
            }
            retval = rdata_write_string(writer, row_name);
            if (retval != RDATA_OK)
                goto cleanup;
        }
    }

    retval = rdata_write_header(writer, RDATA_PSEUDO_SXP_NIL, 0);
    if (retval != RDATA_OK)
        goto cleanup;

    /* Columns added from here on belong to the next table */
    writer->table_first_column = writer->columns_count;
    writer->table_columns_written = 0;
    rdata_writer_free_row_names(writer);

cleanup:
    return retval;
}

rdata_error_t rdata_end_file(rdata_writer_t *writer) {
    rdata_error_t retval = RDATA_OK;

    if (writer->file_format == RDATA_WORKSPACE) {
        retval = rdata_write_header(writer, RDATA_PSEUDO_SXP_NIL, 0);
        if (retval != RDATA_OK)
            goto cleanup;
    }

#if HAVE_ZLIB
    if (writer->compression_ctx) {
        retval = rdata_gzip_write(writer, NULL, 0, Z_FINISH);
        rdata_writer_free_compression(writer);
        if (retval != RDATA_OK)
            goto cleanup;
    }
#endif

cleanup:
    return retval;
}
