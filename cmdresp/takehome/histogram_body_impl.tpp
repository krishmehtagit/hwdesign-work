#include "include/histogram_cmd_hdr.h"
#include "include/histogram_resp_hdr.h"

namespace histogram_impl {
static inline ap_uint<8> ec(HistogramError e) { return (ap_uint<8>)(int)e; }

template <int W>
void body(hls::stream<streamutils::axi4s_word<W>>& s_in,
          hls::stream<streamutils::axi4s_word<W>>& m_out,
          ap_uint<1>& halted, ap_uint<8>& error, ap_uint<16>& tx_id) {
#pragma HLS INLINE
    static ap_uint<32> count[256];
#pragma HLS BIND_STORAGE variable=count type=ram_2p impl=bram
    ap_int<16> lo = 0; ap_uint<8> shift = 0; ap_uint<16> nbins = 0;
    ap_uint<32> below = 0, above = 0; bool configured = false;
    halted=0; error=ec(HistogramError::NO_ERROR); tx_id=0;
    while (true) {
        ap_uint<32> hw[3]; bool last=false, early=false;
        for (int i=0;i<3;i++) {
#pragma HLS PIPELINE II=1
            streamutils::axi4s_word<W> w=s_in.read(); hw[i]=w.data; last=(bool)w.last;
            if (last && i!=2) {
                // The tx_id is entirely in header word zero, so an early header
                // TLAST halts without consuming words after that malformed burst.
                halted=1; error=ec(HistogramError::HEADER_TLAST_EARLY);
                tx_id=(i==0) ? w.data.range(23,8) : hw[0].range(23,8);
                return;
            }
        }
        HistogramCmdHdr h; h.template read_array<32>(hw);
        if (!last) { halted=1; error=ec(HistogramError::HEADER_TLAST_MISSING); tx_id=h.tx_id; return; }
        if (h.code>3) { halted=1; error=ec(HistogramError::UNKNOWN_COMMAND); tx_id=h.tx_id; return; }
        if ((h.code==1 || h.code==2) && !configured) { halted=1; error=ec(HistogramError::NO_CONFIG); tx_id=h.tx_id; return; }
        if (h.code==0) {
            if (h.nbins==0 || h.nbins>256 || h.shift>15) { halted=1; error=ec(HistogramError::BAD_PARAM); tx_id=h.tx_id; return; }
            lo=h.lo; shift=h.shift; nbins=h.nbins; below=0; above=0; configured=true;
            for(int i=0;i<256;i++) {
#pragma HLS PIPELINE II=1
                count[i]=0;
            }
        } else if (h.code==1) {
            if (h.nsamp==0 || h.nsamp>4096) { halted=1; error=ec(HistogramError::BAD_PARAM); tx_id=h.tx_id; return; }
            ap_uint<8> data_error=ec(HistogramError::NO_ERROR);
            for(int i=0;i<h.nsamp;i++) {
#pragma HLS PIPELINE II=1
                if (i<h.nsamp) { streamutils::axi4s_word<W> w=s_in.read(); ap_int<16> x=(ap_int<16>)w.data.range(15,0); ap_int<32> off=(ap_int<32>)x-(ap_int<32>)lo; if(off<0) below++; else { ap_uint<32> b=((ap_uint<32>)off)>>shift; if(b>=nbins) above++; else count[b]++; } if((bool)w.last && i!=h.nsamp-1) { data_error=ec(HistogramError::TLAST_EARLY_SAMP_IN); break; } if(i==h.nsamp-1 && !(bool)w.last) data_error=ec(HistogramError::NO_TLAST_SAMP_IN); }
            }
            if (data_error!=ec(HistogramError::NO_ERROR)) { halted=1; error=data_error; tx_id=h.tx_id; return; }
            // DATA acknowledges only after a completely valid sample burst.
            HistogramRespHdr r; r.tx_id=h.tx_id; r.ndata=0; r.template write_axi4_stream<32>(m_out,true);
        } else if (h.code==2) {
            HistogramRespHdr r; r.tx_id=h.tx_id; r.ndata=nbins+2; r.template write_axi4_stream<32>(m_out,true);
            for(int i=0;i<256;i++) {
#pragma HLS PIPELINE II=1
                if(i<nbins) streamutils::write_axi4_word<32>(m_out,count[i],false);
            }
            streamutils::write_axi4_word<32>(m_out,below,false); streamutils::write_axi4_word<32>(m_out,above,true);
        } else return;
    }
}
} // namespace histogram_impl
