# Clamp and count results

The Waveflow `stream_inband` accelerator is implemented in `clamp_count/`. The frozen Python protocol model and Vitis HLS C simulation both compare every output word, burst boundary, TLAST flag, and final status register against the independently generated Stage 1 expectations.

| Scenario | Python model | C simulation | Python evidence | C-simulation evidence |
| --- | --- | --- | --- | --- |
| worked_example | PASS | PASS | `clamp_count/results/check_model.json` (`w32/worked_example`) | `clamp_count/ecs_csim/data/w32/worked_example/csim/{words.bin,tlast.bin,status.json}` |
| reconfig_resets_count | PASS | PASS | `clamp_count/results/check_model.json` (`w32/reconfig_resets_count`) | `clamp_count/ecs_csim/data/w32/reconfig_resets_count/csim/{words.bin,tlast.bin,status.json}` |
| nsamp_1 | PASS | PASS | `clamp_count/results/check_model.json` (`w32/nsamp_1`) | `clamp_count/ecs_csim/data/w32/nsamp_1/csim/{words.bin,tlast.bin,status.json}` |
| nsamp_1024 | PASS | PASS | `clamp_count/results/check_model.json` (`w32/nsamp_1024`) | `clamp_count/ecs_csim/data/w32/nsamp_1024/csim/{words.bin,tlast.bin,status.json}` |
| equal_bounds_nan_negzero | PASS | PASS | `clamp_count/results/check_model.json` (`w32/equal_bounds_nan_negzero`) | `clamp_count/ecs_csim/data/w32/equal_bounds_nan_negzero/csim/{words.bin,tlast.bin,status.json}` |
| unknown_command | PASS | PASS | `clamp_count/results/check_model.json` (`w32/unknown_command`) | `clamp_count/ecs_csim/data/w32/unknown_command/csim/{words.bin,tlast.bin,status.json}` |
| fresh_after_unknown | PASS | PASS | `clamp_count/results/check_model.json` (`w32/fresh_after_unknown`) | `clamp_count/ecs_csim/data/w32/fresh_after_unknown/csim/{words.bin,tlast.bin,status.json}` |
| data_before_config | PASS | PASS | `clamp_count/results/check_model.json` (`w32/data_before_config`) | `clamp_count/ecs_csim/data/w32/data_before_config/csim/{words.bin,tlast.bin,status.json}` |
| fresh_after_data_before_config | PASS | PASS | `clamp_count/results/check_model.json` (`w32/fresh_after_data_before_config`) | `clamp_count/ecs_csim/data/w32/fresh_after_data_before_config/csim/{words.bin,tlast.bin,status.json}` |
| count_before_config | PASS | PASS | `clamp_count/results/check_model.json` (`w32/count_before_config`) | `clamp_count/ecs_csim/data/w32/count_before_config/csim/{words.bin,tlast.bin,status.json}` |
| fresh_after_count_before_config | PASS | PASS | `clamp_count/results/check_model.json` (`w32/fresh_after_count_before_config`) | `clamp_count/ecs_csim/data/w32/fresh_after_count_before_config/csim/{words.bin,tlast.bin,status.json}` |
| bad_config_nan | PASS | PASS | `clamp_count/results/check_model.json` (`w32/bad_config_nan`) | `clamp_count/ecs_csim/data/w32/bad_config_nan/csim/{words.bin,tlast.bin,status.json}` |
| fresh_after_bad_config | PASS | PASS | `clamp_count/results/check_model.json` (`w32/fresh_after_bad_config`) | `clamp_count/ecs_csim/data/w32/fresh_after_bad_config/csim/{words.bin,tlast.bin,status.json}` |
| bad_nsamp_zero | PASS | PASS | `clamp_count/results/check_model.json` (`w32/bad_nsamp_zero`) | `clamp_count/ecs_csim/data/w32/bad_nsamp_zero/csim/{words.bin,tlast.bin,status.json}` |
| fresh_after_bad_nsamp | PASS | PASS | `clamp_count/results/check_model.json` (`w32/fresh_after_bad_nsamp`) | `clamp_count/ecs_csim/data/w32/fresh_after_bad_nsamp/csim/{words.bin,tlast.bin,status.json}` |
| early_tlast | PASS | PASS | `clamp_count/results/check_model.json` (`w32/early_tlast`) | `clamp_count/ecs_csim/data/w32/early_tlast/csim/{words.bin,tlast.bin,status.json}` |
| fresh_after_early_tlast | PASS | PASS | `clamp_count/results/check_model.json` (`w32/fresh_after_early_tlast`) | `clamp_count/ecs_csim/data/w32/fresh_after_early_tlast/csim/{words.bin,tlast.bin,status.json}` |
| missing_tlast | PASS | PASS | `clamp_count/results/check_model.json` (`w32/missing_tlast`) | `clamp_count/ecs_csim/data/w32/missing_tlast/csim/{words.bin,tlast.bin,status.json}` |
| fresh_after_missing_tlast | PASS | PASS | `clamp_count/results/check_model.json` (`w32/fresh_after_missing_tlast`) | `clamp_count/ecs_csim/data/w32/fresh_after_missing_tlast/csim/{words.bin,tlast.bin,status.json}` |

## Error status

Status registers for each error scenario. Expected values are from `clamp_count/ecs_csim/data/w32/<scenario>/expected_status.json`, and observed C-simulation values are from `clamp_count/ecs_csim/data/w32/<scenario>/csim/status.json`. The model's `model/status.json` matches in every row. Each fresh activation afterward reports `halted=0`, `error=0`, `tx_id=0`.

| Error scenario | Error | Expected halted | Expected error | Expected tx_id | Observed halted | Observed error | Observed tx_id | Fresh activation | Fresh result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| unknown_command | `UNKNOWN_COMMAND` | 1 | 3 | 16 | 1 | 3 | 16 | fresh_after_unknown | PASS |
| data_before_config | `NOT_CONFIGURED` | 1 | 4 | 17 | 1 | 4 | 17 | fresh_after_data_before_config | PASS |
| count_before_config | `NOT_CONFIGURED` | 1 | 4 | 18 | 1 | 4 | 18 | fresh_after_count_before_config | PASS |
| bad_config_nan | `BAD_PARAM` | 1 | 5 | 19 | 1 | 5 | 19 | fresh_after_bad_config | PASS |
| bad_nsamp_zero | `BAD_PARAM` | 1 | 5 | 20 | 1 | 5 | 20 | fresh_after_bad_nsamp | PASS |
| early_tlast | Early TLAST | 1 | 1 | 21 | 1 | 1 | 21 | fresh_after_early_tlast | PASS |
| missing_tlast | Missing TLAST | 1 | 2 | 23 | 1 | 2 | 23 | fresh_after_missing_tlast | PASS |

## C simulation

- Command: `python clamp_count_build.py --through check_csim` on `ecs03.poly.edu`, using `~/ECE_6463/.venv` and `WAVEFLOW_VITIS_PATH=/eda/xilinx/2026.1/Vitis/bin/vitis-run`.
- Result: Vitis reports `CSim done with 0 errors`; Waveflow `check_csim` passes all 19 listed scenarios.
- Complete build log: `clamp_count/ecs_csim/csim_remote.log`.
- Checker report: `clamp_count/ecs_csim/results/check_csim.json`.
- Captured C-simulation burst output and status for every scenario: `clamp_count/ecs_csim/data/w32/<scenario>/csim/`.

`missing_tlast` is checked by the pure Python model rather than pysim, because the pysim stream interface cannot express a burst whose final word lacks TLAST. It is nevertheless checked and passes in C simulation.

## Decisions made where the prompt was silent

- The uint8 command opcode is `CONFIG=0`, `DATA=1`, `COUNT=2`, and `END=3`; all remaining values raise `UNKNOWN_COMMAND=3`.
- Error codes retain the frame's TLAST values (`1`, `2`) and use `UNKNOWN_COMMAND=3`, `NOT_CONFIGURED=4`, and `BAD_PARAM=5`.
- All command headers carry `cmd_type`, `tx_id`, `nsamp`, `lo`, and `hi`. Fields irrelevant to a command are zero and ignored.
- DATA responses use a two-word response header (`tx_id`, `count=0`) followed by the sample burst. COUNT uses the same header with the accumulated count and no data burst. CONFIG and END have no response.
- Only DATA validates `nsamp`; it must be 1 through 1024. CONFIG validates that neither bound is NaN and that `lo <= hi`.
- The 32-bit count increments once for each selected low or high clamp and wraps modulo `2^32`.
- Fixed-size headers do not validate TLAST; DATA sample bursts do. Header-detected errors have no output; framing errors close the already-open output sample burst with TLAST.
- The prompt requests 32-bit streams, so the scaffold's unused 64-bit variant was removed.

## Environment note

The ECS virtual environment lacks Waveflow's newer `TimedPhase` and newer synthesis-step API. The source uses a compatibility guard for the timing-only import, and the build DAG intentionally ends at `check_csim`; no synthesis or cosimulation was run.
