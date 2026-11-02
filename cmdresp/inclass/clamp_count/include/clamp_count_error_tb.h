#ifndef INCLUDE_CLAMP_COUNT_ERROR_TB_H
#define INCLUDE_CLAMP_COUNT_ERROR_TB_H

#include <cctype>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>
#include "streamutils_tb.h"

#define WAVEFLOW_ENABLE_CLAMP_COUNT_ERROR_TB_H_MEMBERS
#include "clamp_count_error.h"
#undef WAVEFLOW_ENABLE_CLAMP_COUNT_ERROR_TB_H_MEMBERS

inline const char* enum_to_string(ClampCountError value) {
    switch (value) {
    case ClampCountError::NO_ERROR:
        return "NO_ERROR";
    case ClampCountError::TLAST_EARLY_SAMP_IN:
        return "TLAST_EARLY_SAMP_IN";
    case ClampCountError::NO_TLAST_SAMP_IN:
        return "NO_TLAST_SAMP_IN";
    case ClampCountError::UNKNOWN_COMMAND:
        return "UNKNOWN_COMMAND";
    case ClampCountError::NOT_CONFIGURED:
        return "NOT_CONFIGURED";
    case ClampCountError::BAD_PARAM:
        return "BAD_PARAM";
    default:
        return "UNKNOWN";
    }
}

#endif // INCLUDE_CLAMP_COUNT_ERROR_TB_H