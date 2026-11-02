#ifndef INCLUDE_HISTOGRAM_ERROR_H
#define INCLUDE_HISTOGRAM_ERROR_H

#include <ap_int.h>
#include <hls_stream.h>
#if __has_include(<hls_axi_stream.h>)
#include <hls_axi_stream.h>
#else
#include <ap_axi_sdata.h>
#endif
#include "streamutils_hls.h"

enum class HistogramError {
    NO_ERROR = 0,
    HEADER_TLAST_EARLY = 1,
    HEADER_TLAST_MISSING = 2,
    UNKNOWN_COMMAND = 3,
    NO_CONFIG = 4,
    BAD_PARAM = 5,
    TLAST_EARLY_SAMP_IN = 6,
    NO_TLAST_SAMP_IN = 7,
};

#endif // INCLUDE_HISTOGRAM_ERROR_H