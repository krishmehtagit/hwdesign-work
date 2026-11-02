#ifndef INCLUDE_CLAMP_COUNT_ERROR_H
#define INCLUDE_CLAMP_COUNT_ERROR_H

#include <ap_int.h>
#include <hls_stream.h>
#if __has_include(<hls_axi_stream.h>)
#include <hls_axi_stream.h>
#else
#include <ap_axi_sdata.h>
#endif
#include "streamutils_hls.h"

enum class ClampCountError {
    NO_ERROR = 0,
    TLAST_EARLY_SAMP_IN = 1,
    NO_TLAST_SAMP_IN = 2,
    UNKNOWN_COMMAND = 3,
    NOT_CONFIGURED = 4,
    BAD_PARAM = 5,
};

#endif // INCLUDE_CLAMP_COUNT_ERROR_H