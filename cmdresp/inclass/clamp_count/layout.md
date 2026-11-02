# Wire layout

Waveflow serialization at 32 bits produced command `[0x001234ab, 0x00005678, 0x3f800000, 0x40000000]` for opcode `0xab`, tx_id `0x1234`, nsamp `0x5678`, lo `1.0`, hi `2.0`; response `[0x00001234, 0x89abcdef]` for tx_id `0x1234`, count `0x89abcdef`. Headers and samples are never hand-packed.

## Command header

| Word | Bits | Field | Type |
| --- | --- | --- | --- |
| 0 | 7:0 | cmd_type | uint8 |
| 0 | 23:8 | tx_id | uint16 |
| 1 | 15:0 | nsamp | uint16 |
| 2 | 31:0 | lo | float32 |
| 3 | 31:0 | hi | float32 |

## Response header

| Word | Bits | Field | Type |
| --- | --- | --- | --- |
| 0 | 15:0 | tx_id | uint16 |
| 1 | 31:0 | count | uint32 |

## Sample burst

One float32 sample is serialized per 32-bit word, preserving its IEEE-754 bits. TLAST belongs only to the final sample word of a successful DATA burst, or the word that detects a framing error.

## Decisions

1. Configuration lives only in `CONFIG(lo, hi)` and persists within one activation. Each `CONFIG` resets the unsigned 32-bit count.
2. `CONFIG` and `END` have no response. `DATA` returns a response header then samples; `COUNT` returns only its response header.
3. `DATA.nsamp` is legal only in `[1, 1024]`; other commands ignore it and send zero.
4. Error precedence is unknown command, unconfigured DATA/COUNT, invalid bounds or nsamp, early TLAST, then missing TLAST.
5. Waveflow serializes every header and response at 32 bits; Waveflow float-array utilities serialize samples.
6. The arithmetic is float32: `if x < lo`, then `elif x > hi`, otherwise pass x through. NaNs pass unchanged and are not counted; `-0.0` is preserved unless a comparison selects a bound.
7. Status `tx_id` is the offending command's transaction ID and is zero after clean END.
8. Only the variable-length DATA sample burst checks TLAST; fixed-size headers do not.
9. The uint8 opcode assigns CONFIG=0, DATA=1, COUNT=2, END=3; all other values halt with `UNKNOWN_COMMAND`.
10. There is no footer: COUNT fits in the response header and the offending command has no output on a header-detected error.
