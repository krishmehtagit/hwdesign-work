#ifndef INCLUDE_HISTOGRAM_ERROR_TB_H
#define INCLUDE_HISTOGRAM_ERROR_TB_H

#include <cctype>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>
#include "streamutils_tb.h"

#define WAVEFLOW_ENABLE_HISTOGRAM_ERROR_TB_H_MEMBERS
#include "histogram_error.h"
#undef WAVEFLOW_ENABLE_HISTOGRAM_ERROR_TB_H_MEMBERS

inline const char* enum_to_string(HistogramError value) {
    switch (value) {
    case HistogramError::NO_ERROR:
        return "NO_ERROR";
    case HistogramError::HEADER_TLAST_EARLY:
        return "HEADER_TLAST_EARLY";
    case HistogramError::HEADER_TLAST_MISSING:
        return "HEADER_TLAST_MISSING";
    case HistogramError::UNKNOWN_COMMAND:
        return "UNKNOWN_COMMAND";
    case HistogramError::NO_CONFIG:
        return "NO_CONFIG";
    case HistogramError::BAD_PARAM:
        return "BAD_PARAM";
    case HistogramError::TLAST_EARLY_SAMP_IN:
        return "TLAST_EARLY_SAMP_IN";
    case HistogramError::NO_TLAST_SAMP_IN:
        return "NO_TLAST_SAMP_IN";
    default:
        return "UNKNOWN";
    }
}

#endif // INCLUDE_HISTOGRAM_ERROR_TB_H