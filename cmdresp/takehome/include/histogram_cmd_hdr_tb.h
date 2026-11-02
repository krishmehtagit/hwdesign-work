#ifndef INCLUDE_HISTOGRAM_CMD_HDR_TB_H
#define INCLUDE_HISTOGRAM_CMD_HDR_TB_H

#include <cctype>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>
#include "streamutils_tb.h"

#define WAVEFLOW_ENABLE_HISTOGRAM_CMD_HDR_TB_H_MEMBERS
#include "histogram_cmd_hdr.h"
#undef WAVEFLOW_ENABLE_HISTOGRAM_CMD_HDR_TB_H_MEMBERS

inline void HistogramCmdHdr::dump_json(std::ostream& os, int indent, int level) const {
    const int step = (indent < 0) ? 0 : indent;
    os << "{";
    os << "\n";
    for (int i = 0; i < (level + 1) * step; ++i) { os << ' '; }
    os << "\"code\": ";
    os << static_cast<unsigned long long>(this->code);
    os << ",";
    os << "\n";
    for (int i = 0; i < (level + 1) * step; ++i) { os << ' '; }
    os << "\"tx_id\": ";
    os << static_cast<unsigned long long>(this->tx_id);
    os << ",";
    os << "\n";
    for (int i = 0; i < (level + 1) * step; ++i) { os << ' '; }
    os << "\"lo\": ";
    os << static_cast<long long>(this->lo);
    os << ",";
    os << "\n";
    for (int i = 0; i < (level + 1) * step; ++i) { os << ' '; }
    os << "\"shift\": ";
    os << static_cast<unsigned long long>(this->shift);
    os << ",";
    os << "\n";
    for (int i = 0; i < (level + 1) * step; ++i) { os << ' '; }
    os << "\"nbins\": ";
    os << static_cast<unsigned long long>(this->nbins);
    os << ",";
    os << "\n";
    for (int i = 0; i < (level + 1) * step; ++i) { os << ' '; }
    os << "\"nsamp\": ";
    os << static_cast<unsigned long long>(this->nsamp);
    os << "\n";
    for (int i = 0; i < (level) * step; ++i) { os << ' '; }
    os << "}";
}

inline void HistogramCmdHdr::load_json(const std::string& json_text, size_t& pos) {
    streamutils::json_expect_char(json_text, pos, '{');
    bool seen_root_code = false;
    bool seen_root_tx_id = false;
    bool seen_root_lo = false;
    bool seen_root_shift = false;
    bool seen_root_nbins = false;
    bool seen_root_nsamp = false;
    bool first = true;
    while (true) {
    streamutils::json_skip_ws(json_text, pos);
    if (pos < json_text.size() && json_text[pos] == '}') {
        ++pos;
        break;
    }
    if (!first) {
        streamutils::json_expect_char(json_text, pos, ',');
    }
    first = false;
    std::string key = streamutils::json_parse_string(json_text, pos);
    streamutils::json_expect_char(json_text, pos, ':');
    if (key == "code") {
        seen_root_code = true;
        this->code = static_cast<ap_uint<8>>(static_cast<unsigned long long>(streamutils::json_parse_number(json_text, pos)));
    }
    else if (key == "tx_id") {
        seen_root_tx_id = true;
        this->tx_id = static_cast<ap_uint<16>>(static_cast<unsigned long long>(streamutils::json_parse_number(json_text, pos)));
    }
    else if (key == "lo") {
        seen_root_lo = true;
        this->lo = static_cast<ap_int<16>>(static_cast<long long>(streamutils::json_parse_number(json_text, pos)));
    }
    else if (key == "shift") {
        seen_root_shift = true;
        this->shift = static_cast<ap_uint<8>>(static_cast<unsigned long long>(streamutils::json_parse_number(json_text, pos)));
    }
    else if (key == "nbins") {
        seen_root_nbins = true;
        this->nbins = static_cast<ap_uint<16>>(static_cast<unsigned long long>(streamutils::json_parse_number(json_text, pos)));
    }
    else if (key == "nsamp") {
        seen_root_nsamp = true;
        this->nsamp = static_cast<ap_uint<16>>(static_cast<unsigned long long>(streamutils::json_parse_number(json_text, pos)));
    }
    else {
        throw std::runtime_error("Malformed JSON: unexpected key for schema.");
    }
    }
    if (!seen_root_code) {
    throw std::runtime_error("Malformed JSON: missing required key 'code'.");
    }
    if (!seen_root_tx_id) {
    throw std::runtime_error("Malformed JSON: missing required key 'tx_id'.");
    }
    if (!seen_root_lo) {
    throw std::runtime_error("Malformed JSON: missing required key 'lo'.");
    }
    if (!seen_root_shift) {
    throw std::runtime_error("Malformed JSON: missing required key 'shift'.");
    }
    if (!seen_root_nbins) {
    throw std::runtime_error("Malformed JSON: missing required key 'nbins'.");
    }
    if (!seen_root_nsamp) {
    throw std::runtime_error("Malformed JSON: missing required key 'nsamp'.");
    }
}

inline void HistogramCmdHdr::load_json(std::istream& is) {
    std::string json_text((std::istreambuf_iterator<char>(is)), std::istreambuf_iterator<char>());
    size_t pos = 0;
    streamutils::json_skip_ws(json_text, pos);
    this->load_json(json_text, pos);
    streamutils::json_skip_ws(json_text, pos);
    if (pos != json_text.size()) {
        throw std::runtime_error("Trailing characters after JSON object.");
    }
}

inline void HistogramCmdHdr::dump_json_file(const char* file_path, int indent) const {
    std::ofstream ofs(file_path);
    if (!ofs) {
        throw std::runtime_error("Failed to open output JSON file.");
    }
    this->dump_json(ofs, indent);
}

inline void HistogramCmdHdr::load_json_file(const char* file_path) {
    std::ifstream ifs(file_path);
    if (!ifs) {
        throw std::runtime_error("Failed to open input JSON file.");
    }
    this->load_json(ifs);
}

#endif // INCLUDE_HISTOGRAM_CMD_HDR_TB_H