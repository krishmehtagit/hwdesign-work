#ifndef INCLUDE_HISTOGRAM_CMD_HDR_H
#define INCLUDE_HISTOGRAM_CMD_HDR_H

#include <ap_int.h>
#include <hls_stream.h>
#if __has_include(<hls_axi_stream.h>)
#include <hls_axi_stream.h>
#else
#include <ap_axi_sdata.h>
#endif
#include "streamutils_hls.h"

struct HistogramCmdHdr {
    ap_uint<8> code;  // CONFIG=0, DATA=1, READ=2, END=3
    ap_uint<16> tx_id;  // transaction ID
    ap_int<16> lo;  // CONFIG lower edge; ignored otherwise
    ap_uint<8> shift;  // CONFIG bin width exponent
    ap_uint<16> nbins;  // CONFIG bin count
    ap_uint<16> nsamp;  // DATA sample count

    static constexpr int bitwidth = 80;

    template<int word_bw>
    struct word_bw_tag {};

    template<int word_bw>
    static constexpr int nwords_value(word_bw_tag<word_bw>) {
            static_assert(word_bw < 0, "Unsupported word_bw for nwords");
            return 0;
    }

    static constexpr int nwords_value(word_bw_tag<32>) {
            return 3;
    }

    template<int word_bw>
    static constexpr int nwords() {
        return nwords_value(word_bw_tag<word_bw>{});
    }

    static ap_uint<bitwidth> pack_to_uint(const HistogramCmdHdr& data) {
        ap_uint<bitwidth> res = 0;
        res.range(7, 0) = data.code;
        res.range(23, 8) = data.tx_id;
        res.range(39, 24) = data.lo;
        res.range(47, 40) = data.shift;
        res.range(63, 48) = data.nbins;
        res.range(79, 64) = data.nsamp;
        return res;
    }

    static HistogramCmdHdr unpack_from_uint(const ap_uint<bitwidth>& packed) {
        HistogramCmdHdr data;
        data.code = (ap_uint<8>)(packed.range(7, 0));
        data.tx_id = (ap_uint<16>)(packed.range(23, 8));
        data.lo = (ap_int<16>)(packed.range(39, 24));
        data.shift = (ap_uint<8>)(packed.range(47, 40));
        data.nbins = (ap_uint<16>)(packed.range(63, 48));
        data.nsamp = (ap_uint<16>)(packed.range(79, 64));
        return data;
    }

    template<int word_bw>
    static void write_array_impl(word_bw_tag<word_bw>, const HistogramCmdHdr* self, ap_uint<word_bw> x[]) {
        static_assert(word_bw < 0, "Unsupported word_bw for write_array");
        (void)self;
        (void)x;
    }

    static void write_array_impl(word_bw_tag<32>, const HistogramCmdHdr* self, ap_uint<32> x[]) {
        x[0] = 0;
        x[0].range(7, 0) = self->code;
        x[0].range(23, 8) = self->tx_id;
        x[1] = 0;
        x[1].range(15, 0) = self->lo;
        x[1].range(23, 16) = self->shift;
        x[2] = 0;
        x[2].range(15, 0) = self->nbins;
        x[2].range(31, 16) = self->nsamp;
    }

    template<int word_bw>
    void write_array(ap_uint<word_bw> x[]) const {
        write_array_impl(word_bw_tag<word_bw>{}, this, x);
    }

    template<int word_bw>
    static void write_stream_impl(word_bw_tag<word_bw>, const HistogramCmdHdr* self, hls::stream<ap_uint<word_bw>> &s) {
        static_assert(word_bw < 0, "Unsupported word_bw for write_stream");
        (void)self;
        (void)s;
    }

    static void write_stream_impl(word_bw_tag<32>, const HistogramCmdHdr* self, hls::stream<ap_uint<32>> &s) {
            ap_uint<32> w = 0;
        w.range(7, 0) = self->code;
        w.range(23, 8) = self->tx_id;
        s.write(w);
        w = 0;
        w.range(15, 0) = self->lo;
        w.range(23, 16) = self->shift;
        s.write(w);
        w = 0;
        w.range(15, 0) = self->nbins;
        w.range(31, 16) = self->nsamp;
        s.write(w);
        w = 0;
    }

    template<int word_bw>
    void write_stream(hls::stream<ap_uint<word_bw>> &s) const {
        write_stream_impl(word_bw_tag<word_bw>{}, this, s);
    }

    template<int word_bw>
    static void write_axi4_stream_impl(word_bw_tag<word_bw>, const HistogramCmdHdr* self, hls::stream<streamutils::axi4s_word<word_bw>> &s, bool tlast) {
        static_assert(word_bw < 0, "Unsupported word_bw for write_axi4_stream");
        (void)self;
        (void)s;
        (void)tlast;
    }

    static void write_axi4_stream_impl(word_bw_tag<32>, const HistogramCmdHdr* self, hls::stream<streamutils::axi4s_word<32>> &s, bool tlast) {
            ap_uint<32> w = 0;
        w.range(7, 0) = self->code;
        w.range(23, 8) = self->tx_id;
        streamutils::write_axi4_word<32>(s, w, false);
        w = 0;
        w.range(15, 0) = self->lo;
        w.range(23, 16) = self->shift;
        streamutils::write_axi4_word<32>(s, w, false);
        w = 0;
        w.range(15, 0) = self->nbins;
        w.range(31, 16) = self->nsamp;
        streamutils::write_axi4_word<32>(s, w, tlast);
        w = 0;
    }

    template<int word_bw>
    void write_axi4_stream(hls::stream<streamutils::axi4s_word<word_bw>> &s, bool tlast = true) const {
        write_axi4_stream_impl(word_bw_tag<word_bw>{}, this, s, tlast);
    }

    template<int word_bw>
    static void read_array_impl(word_bw_tag<word_bw>, HistogramCmdHdr* self, const ap_uint<word_bw> x[]) {
        static_assert(word_bw < 0, "Unsupported word_bw for read_array");
        (void)self;
        (void)x;
    }

    static void read_array_impl(word_bw_tag<32>, HistogramCmdHdr* self, const ap_uint<32> x[]) {
        self->code = (ap_uint<8>)(x[0].range(7, 0));
        self->tx_id = (ap_uint<16>)(x[0].range(23, 8));
        self->lo = (ap_int<16>)(x[1].range(15, 0));
        self->shift = (ap_uint<8>)(x[1].range(23, 16));
        self->nbins = (ap_uint<16>)(x[2].range(15, 0));
        self->nsamp = (ap_uint<16>)(x[2].range(31, 16));
    }

    template<int word_bw>
    void read_array(const ap_uint<word_bw> x[]) {
        read_array_impl(word_bw_tag<word_bw>{}, this, x);
    }

    template<int word_bw>
    static void read_stream_impl(word_bw_tag<word_bw>, HistogramCmdHdr* self, hls::stream<ap_uint<word_bw>> &s) {
        static_assert(word_bw < 0, "Unsupported word_bw for read_stream");
        (void)self;
        (void)s;
    }

    static void read_stream_impl(word_bw_tag<32>, HistogramCmdHdr* self, hls::stream<ap_uint<32>> &s) {
            ap_uint<32> w = 0;
        w = s.read();
        self->code = (ap_uint<8>)(w.range(7, 0));
        self->tx_id = (ap_uint<16>)(w.range(23, 8));
        w = s.read();
        self->lo = (ap_int<16>)(w.range(15, 0));
        self->shift = (ap_uint<8>)(w.range(23, 16));
        w = s.read();
        self->nbins = (ap_uint<16>)(w.range(15, 0));
        self->nsamp = (ap_uint<16>)(w.range(31, 16));
    }

    template<int word_bw>
    void read_stream(hls::stream<ap_uint<word_bw>> &s) {
        read_stream_impl(word_bw_tag<word_bw>{}, this, s);
    }

    template<int word_bw>
    static void read_axi4_stream_impl(word_bw_tag<word_bw>, HistogramCmdHdr* self, hls::stream<streamutils::axi4s_word<word_bw>> &s, streamutils::tlast_status &tl) {
        static_assert(word_bw < 0, "Unsupported word_bw for read_axi4_stream");
        (void)self;
        (void)s;
        (void)tl;
    }

    static void read_axi4_stream_impl(word_bw_tag<32>, HistogramCmdHdr* self, hls::stream<streamutils::axi4s_word<32>> &s, streamutils::tlast_status &tl) {
            ap_uint<32> w = 0;
            tl = streamutils::tlast_status::no_tlast;
            bool last = false;
        if (last) {
            tl = streamutils::tlast_status::tlast_early;
            return;
        }
        {
            auto axis_word = s.read();
            w = axis_word.data;
            last = axis_word.last;
        }
        self->code = (ap_uint<8>)(w.range(7, 0));
        if (tl != streamutils::tlast_status::no_tlast) {
            tl = streamutils::tlast_status::tlast_early;
            return;
        }
        self->tx_id = (ap_uint<16>)(w.range(23, 8));
        if (tl != streamutils::tlast_status::no_tlast) {
            tl = streamutils::tlast_status::tlast_early;
            return;
        }
        if (last) {
            tl = streamutils::tlast_status::tlast_early;
            return;
        }
        {
            auto axis_word = s.read();
            w = axis_word.data;
            last = axis_word.last;
        }
        self->lo = (ap_int<16>)(w.range(15, 0));
        if (tl != streamutils::tlast_status::no_tlast) {
            tl = streamutils::tlast_status::tlast_early;
            return;
        }
        self->shift = (ap_uint<8>)(w.range(23, 16));
        if (tl != streamutils::tlast_status::no_tlast) {
            tl = streamutils::tlast_status::tlast_early;
            return;
        }
        if (last) {
            tl = streamutils::tlast_status::tlast_early;
            return;
        }
        {
            auto axis_word = s.read();
            w = axis_word.data;
            last = axis_word.last;
        }
        self->nbins = (ap_uint<16>)(w.range(15, 0));
        if (tl != streamutils::tlast_status::no_tlast) {
            tl = streamutils::tlast_status::tlast_early;
            return;
        }
        self->nsamp = (ap_uint<16>)(w.range(31, 16));
        if (tl != streamutils::tlast_status::no_tlast) {
            return;
        }
        if (last) {
            tl = streamutils::tlast_status::tlast_at_end;
        }
    }

    template<int word_bw>
    void read_axi4_stream(hls::stream<streamutils::axi4s_word<word_bw>> &s, streamutils::tlast_status &tl) {
        read_axi4_stream_impl(word_bw_tag<word_bw>{}, this, s, tl);
    }

    template<int word_bw>
    void read_axi4_stream(hls::stream<streamutils::axi4s_word<word_bw>> &s) {
        streamutils::tlast_status tl = streamutils::tlast_status::no_tlast;
        read_axi4_stream<word_bw>(s, tl);
    }

#ifdef WAVEFLOW_ENABLE_HISTOGRAM_CMD_HDR_TB_H_MEMBERS
    void dump_json(std::ostream& os, int indent = 2, int level = 0) const;
    void load_json(const std::string& json_text, size_t& pos);
    void load_json(std::istream& is);
    void dump_json_file(const char* file_path, int indent = 2) const;
    void load_json_file(const char* file_path);
#endif
};

#endif // INCLUDE_HISTOGRAM_CMD_HDR_H