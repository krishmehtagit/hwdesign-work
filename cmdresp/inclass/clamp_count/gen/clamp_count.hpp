#pragma once

#include <ap_int.h>
#include <ap_fixed.h>

#include "include/streamutils_hls.h"
#include "include/clamp_count_error.h"

void clamp_count(
    hls::stream<streamutils::axi4s_word<32>>& s_in,
    hls::stream<streamutils::axi4s_word<32>>& m_out,
    ap_uint<1>& halted,
    ap_uint<8>& error,
    ap_uint<16>& tx_id
);

namespace clamp_count_impl {
    template <int in_bw, int out_bw>
    void body(hls::stream<streamutils::axi4s_word<in_bw>>& s_in, hls::stream<streamutils::axi4s_word<out_bw>>& m_out, ap_uint<1>& halted, ap_uint<8>& error, ap_uint<16>& tx_id);
}

#include "../clamp_count_body_impl.tpp"
