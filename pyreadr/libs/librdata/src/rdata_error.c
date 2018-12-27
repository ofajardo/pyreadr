
#include "rdata.h"

const char *rdata_error_message(rdata_error_t error_code) {
    if (error_code == RDATA_OK)
        return NULL;

    if (error_code == RDATA_ERROR_OPEN)
        return "Unable to open file";

    if (error_code == RDATA_ERROR_SEEK)
        return "Unable to seek within file";

    if (error_code == RDATA_ERROR_READ)
        return "Unable to read from file";

    if (error_code == RDATA_ERROR_MALLOC)
        return "Unable to allocate memory";

    if (error_code == RDATA_ERROR_USER_ABORT)
        return "The parsing was aborted (callback returned non-zero value)";

    if (error_code == RDATA_ERROR_PARSE)
        return "Invalid file, or file has unsupported features";

    if (error_code == RDATA_ERROR_WRITE)
        return "Unable to write to file";

    if (error_code == RDATA_ERROR_FACTOR)
        return "The provided column does not support factors";

    if (error_code == RDATA_ERROR_UNSUPPORTED_COMPRESSION)
        return "The file is compressed using an unsupported compression scheme";

    return "Unknown error";
}
