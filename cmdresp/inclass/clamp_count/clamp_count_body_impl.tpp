#include "include/float32_array_utils.h"
#include "include/clamp_count_cmd_hdr.h"
#include "include/clamp_count_resp_hdr.h"

namespace clamp_count_impl {

static inline ap_uint<8> code(ClampCountError error) {
#pragma HLS INLINE
    return static_cast<unsigned int>(error);
}

static inline bool invalid_bounds(float lo, float hi) {
#pragma HLS INLINE
    return lo != lo || hi != hi || lo > hi;
}

static inline float clamp_sample(float x, float lo, float hi, ap_uint<32>& count) {
#pragma HLS INLINE
    if (x < lo) {
        count = count + 1;
        return lo;
    }
    if (x > hi) {
        count = count + 1;
        return hi;
    }
    return x;
}

template <int in_bw, int out_bw>
ap_uint<8> data_transaction(const ClampCountCmdHdr& command,
                            float lo, float hi, ap_uint<32>& count,
                            hls::stream<streamutils::axi4s_word<in_bw>>& s_in,
                            hls::stream<streamutils::axi4s_word<out_bw>>& m_out) {
#pragma HLS INLINE
    ClampCountRespHdr response;
    response.tx_id = command.tx_id;
    response.count = 0;
    response.write_axi4_stream<out_bw>(m_out, true);

    float x_lane[1];
    float y_lane[1];
#pragma HLS ARRAY_PARTITION variable=x_lane complete dim=1
#pragma HLS ARRAY_PARTITION variable=y_lane complete dim=1
    for (int sample = 0; sample < command.nsamp; ++sample) {
#pragma HLS PIPELINE II=1
        streamutils::tlast_status lane_tlast = streamutils::tlast_status::no_tlast;
        float32_array_utils::read_axi4_stream_lane<in_bw>(s_in, x_lane, 1, lane_tlast);
        const bool input_last = lane_tlast == streamutils::tlast_status::tlast_at_end;
        const bool final_sample = sample + 1 == command.nsamp;
        y_lane[0] = clamp_sample(x_lane[0], lo, hi, count);
        float32_array_utils::write_axi4_stream_lane<out_bw>(y_lane, m_out, final_sample || input_last, 1);
        if (input_last && !final_sample) return code(ClampCountError::TLAST_EARLY_SAMP_IN);
        if (final_sample && !input_last) return code(ClampCountError::NO_TLAST_SAMP_IN);
    }
    return code(ClampCountError::NO_ERROR);
}

template <int in_bw, int out_bw>
void body(hls::stream<streamutils::axi4s_word<in_bw>>& s_in,
          hls::stream<streamutils::axi4s_word<out_bw>>& m_out,
          ap_uint<1>& halted, ap_uint<8>& error, ap_uint<16>& tx_id) {
#pragma HLS INLINE
    halted = 0;
    error = code(ClampCountError::NO_ERROR);
    tx_id = 0;
    bool configured = false;
    float lo = 0.0f;
    float hi = 0.0f;
    ap_uint<32> count = 0;
    while (true) {
        ClampCountCmdHdr command;
        command.read_axi4_stream<in_bw>(s_in);
        const unsigned int opcode = command.cmd_type;
        ap_uint<8> command_error = code(ClampCountError::NO_ERROR);
        if (opcode > 3) {
            command_error = code(ClampCountError::UNKNOWN_COMMAND);
        } else if ((opcode == 1 || opcode == 2) && !configured) {
            command_error = code(ClampCountError::NOT_CONFIGURED);
        } else if (opcode == 0) {
            if (invalid_bounds(command.lo, command.hi)) command_error = code(ClampCountError::BAD_PARAM);
            else {
                configured = true;
                lo = command.lo;
                hi = command.hi;
                count = 0;
            }
        } else if (opcode == 1) {
            if (command.nsamp == 0 || command.nsamp > 1024) command_error = code(ClampCountError::BAD_PARAM);
            else command_error = data_transaction<in_bw, out_bw>(command, lo, hi, count, s_in, m_out);
        } else if (opcode == 2) {
            ClampCountRespHdr response;
            response.tx_id = command.tx_id;
            response.count = count;
            response.write_axi4_stream<out_bw>(m_out, true);
        } else {
            return;
        }
        if (command_error != code(ClampCountError::NO_ERROR)) {
            halted = 1;
            error = command_error;
            tx_id = command.tx_id;
            return;
        }
    }
}

}  // namespace clamp_count_impl
