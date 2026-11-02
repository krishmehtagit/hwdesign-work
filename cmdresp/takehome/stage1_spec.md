# Stage 1 specification — streaming histogram

## Chosen architecture

`stream_inband`: one host-launched AXI4-Stream kernel, AXI-Lite used only for
`halted`, `error`, and `tx_id`.  This is the Waveflow reference frame named by
the assignment.

## State and commands

The stream header carries `code` (uint8), `tx_id` (uint16), and the command
parameters.  A CONFIG (`code=0`) carries signed `lo` (int16), unsigned
`shift` (uint8), and unsigned `nbins` (uint16).  DATA (`code=1`) carries
unsigned `nsamp` (uint16); READ (`code=2`) and END (`code=3`) have no active
parameters.  Fixed-length headers use the Waveflow serializer and do not have
TLAST semantics.

A successful CONFIG records `lo`, `shift`, and `nbins`, clears all 256
physical bin registers and both uint32 wraparound counters, and establishes
the activation configuration.  DATA and READ before a successful CONFIG are
errors.  DATA samples are signed int16 in bits [15:0] of a 32-bit stream word;
bits [31:16] are ignored.  For each sample, the widened signed offset is
`int32(sample)-int32(lo)`.  A negative offset increments `below`; otherwise
`offset >> shift >= nbins` increments `above`; otherwise that bin increments.
All counters wrap modulo 2^32.

READ emits `RespHdr(tx_id, nwords=nbins+2)`, then bins `[0,nbins)`, `below`,
and `above`, with TLAST only on `above`.  DATA emits `RespHdr(tx_id,nwords=0)`
only after its final valid sample.  CONFIG and END emit no response; END
returns cleanly.  READ is non-mutating.

## Errors and precedence

Status begins each activation as `{halted:0,error:0,tx_id:0}`.  On error the
kernel closes an already-started response burst with TLAST, then returns
without reading more stream words.  The intended codes are: 1 early/missing
header TLAST framing, 2 unknown command, 3 DATA/READ before CONFIG, 4 invalid
parameter, 5 early DATA TLAST, and 6 missing DATA TLAST.  Exact header-TLAST
handling must be expressed through the Waveflow schema/burst facilities,
never manually packed.  Checks follow the prompt order: header framing,
opcode, CONFIG-seen, parameters, then DATA framing.

## Verification matrix

The frozen scenario set will include hand-calculated boundary values,
NumPy/`bincount` comparison, `nsamp` 1 and 4096, `nbins` 1 and 256, all range
edges, 4096 samples to one bin, configuration clearing between READs, every
invalid parameter value, every error in its own activation, and a fresh valid
activation after each error.  The timing scenario is a 4096-sample same-bin
DATA burst.  Expected outputs will be constructed from scenario intents, not
by the protocol model.

## Decisions

- Configuration is persistent within one activation; only CONFIG changes it.
- A DATA header is accepted only with `1 <= nsamp <= 4096`; no zero-length
  DATA exists because the prompt defines the valid range.
- `nbins` is 1..256 and `shift` is 0..15; invalid CONFIG does not clear state
  and does not establish configuration.
- `lo` and samples are two's-complement int16.  Offset widening precedes the
  range comparison and shift, preventing subtraction overflow.
- Header fields and all response fields are serialized by Waveflow schemas;
  sample payloads use Waveflow array utilities.  No manual word packing.
- `tx_id` reports the command that failed and is zero on clean END.
- Successful CONFIG must clear the inactive physical bins as well as active
  bins so a later larger `nbins` cannot expose stale counts.
