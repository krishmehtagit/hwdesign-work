# Streaming histogram results

## Interface

Waveflow serializes each 32-bit AXI4-Stream command header in three words:
`code[7:0] | tx_id[23:8]`; signed `lo[15:0] | shift[23:16]`; and
`nbins[15:0] | nsamp[31:16]`.  Data uses only the signed low 16 bits.  The
one-word response header has `tx_id[15:0] | nwords[31:16]` (the generated
C++ field is named `ndata` to avoid collision with a generated `nwords()`
method).  DATA responds with `nwords=0`; READ responds with `nbins+2`, followed
by bins, below and above, with TLAST only on above.

AXI-Lite status is `halted`, `error`, and `tx_id`; it clears at activation
start.  Error codes are: 1 early-header TLAST, 2 missing-header TLAST, 3
unknown command, 4 DATA/READ before CONFIG, 5 bad parameter, 6 early-data
TLAST, and 7 missing-data TLAST.

## Design

The activation keeps `lo`, `shift`, `nbins`, 256 uint32 bins, and uint32
below/above counters.  CONFIG clears all counters.  DATA widens the signed
subtraction before classifying below/in-bin/above; counters wrap naturally.
The bin update is a BRAM read-modify-write loop.  Its same-address dependence
is why Vitis scheduled II=2; no timing-closure rework was attempted.

## Targets

| Target | Required | Measured | PASS/FAIL | Source |
| --- | --- | --- | --- | --- |
| Same-bin accepted samples/clock | 0.5 (prompt v7); originally 1.0, which was missed | 0.5 (2.0 cycles per sample) | **PASS** against v7 | [result.transaction.rpt](artifacts/v5/result.transaction.rpt), [synth_cosim_v5.log](artifacts/v5/synth_cosim_v5.log) |
| Same-bin cosim latency | no target | 8,764 cycles (transaction 3) | PASS | [result.transaction.rpt](artifacts/v5/result.transaction.rpt) |
| Full-suite cosim latency | no target | min/avg/max 9 / 634 / 8,764 cycles | PASS | [histogram_cosim.rpt](artifacts/v5/histogram_cosim.rpt) |
| Estimated clock | under 10 ns | 9.060 ns | **PASS** | [histogram_csynth.rpt](artifacts/v5/histogram_csynth.rpt) |
| Resources | no target | 1 BRAM18K, 0 DSP, 969 FF, 1,546 LUT | PASS | [histogram_csynth.rpt](artifacts/v5/histogram_csynth.rpt) |

The accepted-samples/clock value is measured from co-simulation: `nsamp_1`
(transaction 2, 574 cycles) and `same_bin_4096` (transaction 3, 8,764 cycles)
have the same command sequence with 1 and 4096 samples, so the 4095 extra
samples took 8,190 cycles, or 2.0 cycles per sample.  This agrees with the
synthesis II of 2.  The 2.70 ns clock-uncertainty warning does not alter the required
under-10-ns estimated-clock PASS.

## Verification

Hand calculation and independent NumPy `bincount` both pass; exact model,
CSim, and cosim bundle comparisons are recorded in [compare.log](artifacts/v5/compare.log).
Each row below is PASS in all three layers; `E#` gives the asserted error
status and `fresh` marks the immediately following clean activation.

| Scenario | Status/result | Model / CSim / cosim source |
| --- | --- | --- |
| hand_edges | clean | [compare.log](artifacts/v5/compare.log) |
| nbins_256_edges | clean | [compare.log](artifacts/v5/compare.log) |
| nsamp_1 | clean | [compare.log](artifacts/v5/compare.log) |
| same_bin_4096 | clean | [compare.log](artifacts/v5/compare.log) |
| clear | clean, changed second CONFIG | [compare.log](artifacts/v5/compare.log) |
| header_early | E1 | [csim_v4.log](artifacts/v5/csim_v5_verify.log) |
| header_missing | E2 | [csim_v4.log](artifacts/v5/csim_v5_verify.log) |
| unknown_command | E3 | [csim_v4.log](artifacts/v5/csim_v5_verify.log) |
| data_before_config | E4 | [csim_v4.log](artifacts/v5/csim_v5_verify.log) |
| read_before_config | E4 | [csim_v4.log](artifacts/v5/csim_v5_verify.log) |
| bad_nbins_zero | E5 | [csim_v4.log](artifacts/v5/csim_v5_verify.log) |
| bad_nbins_257 | E5 | [csim_v4.log](artifacts/v5/csim_v5_verify.log) |
| bad_shift_16 | E5 | [csim_v4.log](artifacts/v5/csim_v5_verify.log) |
| bad_nsamp_zero | E5 | [csim_v4.log](artifacts/v5/csim_v5_verify.log) |
| bad_nsamp_4097 | E5 | [csim_v4.log](artifacts/v5/csim_v5_verify.log) |
| data_early | E6; no DATA response | [csim_v4.log](artifacts/v5/csim_v5_verify.log) |
| data_missing | E7; no DATA response | [csim_v4.log](artifacts/v5/csim_v5_verify.log) |
| priority_header_unknown | E2 wins | [csim_v4.log](artifacts/v5/csim_v5_verify.log) |
| priority_no_config_bad_nsamp | E4 wins | [csim_v4.log](artifacts/v5/csim_v5_verify.log) |
| fresh_after_header_early | clean | [csim_v4.log](artifacts/v5/csim_v5_verify.log) |
| fresh_after_header_missing | clean | [csim_v4.log](artifacts/v5/csim_v5_verify.log) |
| fresh_after_unknown_command | clean | [csim_v4.log](artifacts/v5/csim_v5_verify.log) |
| fresh_after_data_before_config | clean | [csim_v4.log](artifacts/v5/csim_v5_verify.log) |
| fresh_after_read_before_config | clean | [csim_v4.log](artifacts/v5/csim_v5_verify.log) |
| fresh_after_bad_nbins_zero | clean | [csim_v4.log](artifacts/v5/csim_v5_verify.log) |
| fresh_after_bad_nbins_257 | clean | [csim_v4.log](artifacts/v5/csim_v5_verify.log) |
| fresh_after_bad_shift_16 | clean | [csim_v4.log](artifacts/v5/csim_v5_verify.log) |
| fresh_after_bad_nsamp_zero | clean | [csim_v4.log](artifacts/v5/csim_v5_verify.log) |
| fresh_after_bad_nsamp_4097 | clean | [csim_v4.log](artifacts/v5/csim_v5_verify.log) |
| fresh_after_data_early | clean | [csim_v4.log](artifacts/v5/csim_v5_verify.log) |
| fresh_after_data_missing | clean | [csim_v4.log](artifacts/v5/csim_v5_verify.log) |
| fresh_after_priority_header_unknown | clean | [csim_v4.log](artifacts/v5/csim_v5_verify.log) |
| fresh_after_priority_no_config_bad_nsamp | clean | [csim_v4.log](artifacts/v5/csim_v5_verify.log) |

The saved intent, expected, model, CSim, and cosim bundles are in
[artifacts/v5/w32](artifacts/v5/w32).

## Assumptions

- An early header TLAST stops before reading following header words; tx_id is
  available in word 0.
- Bad CONFIG does not change an existing configuration; every error scenario
  here is a fresh activation.  Settled as a requirement in prompt v6.
- For malformed parameter commands, unconsumed payload is deliberately
  discarded by the testbench reset, as required after a halt.
- An early/missing sample TLAST processes only received samples for state
  purposes but sends no DATA response, per prompt v4.
- Header TLAST has priority over an unknown code; missing CONFIG has priority
  over an invalid DATA nsamp.  The two combined-error scenarios verify both.
- The prompt does not specify CONFIG-header inactive fields, READ/DATA inactive
  fields, END fields, response ordering after a fatal error, or status reset
  cycle; they are serialized as zero by the scenario helper, fatal runs emit
  no new response, and status is observable after return.
- With no first header word, the kernel waits at the stream read; this
  condition is not generated.  Settled as a requirement in prompt v6.

## Open Items

None.  The original target of 1.0 sample per clock was missed (II=2); prompt v7
accepts 0.5 samples per clock.

## Run History

| Prompt version | Work | Outcome |
| --- | --- | --- |
| v2 + approved header correction | Initial CSim and same-bin cosim | CSim/cosim PASS; II=2 FAIL |
| v3 | Added all fixed error codes, invalid parameters, fresh-after-error activations, NumPy/hand oracle, and one full-suite cosim run | 29/29 model, CSim, and cosim exact PASS; II=2 FAIL; 9.060 ns clock PASS |
| v4 | DATA TLAST errors suppress DATA responses; second CONFIG changes all configuration fields; added combined-error precedence tests | 33/33 model, CSim, and cosim exact PASS; II=2 FAIL; 9.060 ns clock PASS |
| v5 | Changed only DATA-loop bound from 4096 to `nsamp`; reran and compared all current outputs | 33/33 model, CSim, and cosim exact PASS; II=2 FAIL; same-bin 8,764 cycles; 9.060 ns clock PASS |
| v6 | Recorded the existing bad-CONFIG and no-first-word behavior as requirements; no kernel change, so no checks were rerun | v5 results stand |
| v7 | Accepted the measured 0.5 samples per clock; reported it from co-simulation transactions; no kernel change, so no checks were rerun | v5 results stand |
