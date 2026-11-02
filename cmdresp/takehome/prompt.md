# Streaming histogram accelerator

Build a Vitis HLS kernel in this folder following the Waveflow stream_inband
example (https://sdrangan.github.io/waveflow/docs/examples/stream_inband/) and
the command-response pattern(https://sdrangan.github.io/hwdesign/docs/labs/cmdresp/pattern.html).
And whenever they are different, follow the pattern. Also, the configuration is a command on stream, not axi light write. Write a bit exact Python model. Do not build a timing model in Python.

Write all files in this folder on the Mac, and do not run any git commands.
So you're supposed to run the Python model on this Mac locally on a virtual environment with Python. This is the path for the virtual environment.   /Users/krishmehta/Desktop/6463/.venv/bin/python
So the simulation, co-simulation synthesis, Vitis is on the ECS server
ecs03.poly.edu as user km6152
copy this folder to server (~/ECE_6463 cmdresp_takehome), run ssh km6152@ecs03.poly edu bash -s with a heredoc. In it, activate
~/ECE_6463/.venv, then run
export WAVEFLOW_VITIS_PATH=/eda/xilinx/2026.1/Vitis/bin/vitis-run

copy the outputs, logs, reports that results.md cites, leave prj_* as it is, Don’t copy

~/ECE_6463/cmdresp_takehome
only touch this one server
do not change shell startup files

## Operation
Our operation is that kernel will count 16-bit signed samples into nbins bins of equal width with 2^shift Bin i holds the samples from lo + i * 2^shift to lo + (i + 1) * 2^shift - 1
x sample, we are supposed to compute a width that cannot overflow. So if the offset is equal to x minus lo, then if offset is negative, then below is below plus 1. If offset shifts right for "shift bits", okay, if that's greater than or equal to n bins, then above is equal to above plus 1. And if both are false conditions, then count[offset >> shift] = count[offset >> shift] + 1 The states are lo, shift, and bins. The bin counts below and above. All of them will carry one command to the next within an activation. The bin counts below and above are unsigned 32-bit and wrap modulo 2 power 32. They accumulate across data commands. Only config can clear them. Read does not change them.
Every successful CONFIG clears all bins, below and above.

## Requirements
A few requirements that we should keep in mind is sample and LO are signed 16-bit and counts are assigned unsigned 32-bit. The ACI-4 stream words are 32-bit. Each word carries one sample in its lower 16 bits and the upper 16 bits are just ignored. Largest sizes for N bins is 256 and N samp up to 4096 in one data command. A throughput target is one sample per clock during data burst, measured in co simulation on a 4096 sample burst where every sample lands in the same bin. And our consecutive samples in the same bin must still be counted correctly. One sample per clock means one input word accepted per clock from the first sample to the last sample. Our clock target is what is estimated a clock should be under 10 nanoseconds. There is no latency or resource target, so CONFIG may stall the input while it clears the count, but it's fine.Same bin throughput of 0.5 accepted samples per clock (II=2) is accepted, one sample per clock is a thing that is required.

## Commands and parameters
For each of our command headers is one fixed length burst ending in tlast, and it carries a txid. Each response will start with a response header, a burst ending with tlast that carries the command's txid and nwords, the number of data words after it.

CONFIG (code 0) in this header carries lo (int16), shift (uint8) and nbins (uint16).
No data will follows and no response will be there
DATA (code 1) nsamp, then nsamp samples ending in TLAST.
Response: header with nwords = 0, after the last sample.
READ (code 2) response is a header with nwords = nbins + 2, then count[0] to count[nbins-1], below, above, with TLAST on above.
END (code 3) no response. The kernel returns.
Valid values: nbins 1 to 256, shift 0 to 15, nsamp 1 to 4096. Check them before reading data.

The DATA loop runs only nsamp times. On an early or missing sample TLAST, send no response for that DATA command.

## Errors
Errors go in AXI-Lite status registers (halted, error code, tx_id).  On an
error the kernel closes any output burst it started with TLAST and returns
without reading more input.  Nothing persists between activations: the status
registers are cleared at the start of each one.

Check in this particular order
First, try checking that if the tlast came early or is missing. Then you can check if there was an unknown command. Then you can check if before we sent config in this activation, if there was a data or a read, then check if nbin shift or nsamp is outside the valid range, like if it's a bad parameter. Then check if tlast was on the data sample before the samples nsamp. Check if there was no tlast sent.

## Verification
Check the Python model against a NumPy reference built with np.bincount, and
against hand-computed examples computed by you
Huge difference in ideas also, like NSAMP 1 and 4096, NBINs 1 and 256. Same for edges and samples. Then like 4096 samples in same bins, a config between commands, with reach showing old counts were cleared, each error in its own activation, each invalid parameter value, try different scenarios and check. After each error, a fresh activation must pass, right!

Compare the model, C simulation and co-simulation bit for bit.  Run
co-simulation once: one testbench run that walks through every scenario in
order, calling the kernel once per activation with fresh streams, including
each error activation and the fresh activation after it.

Error codes: 1 early header TLAST, 2 missing header TLAST, 3 unknown command, 4 DATA or READ before CONFIG, 5 bad parameter, 6 early data TLAST, 7 missing data TLAST.
Run every scenario in the Python model, C simulation and co-simulation. Report accepted samples per clock from co-simulation.

The second CONFIG test must change lo, shift and nbins. Test two errors at once to confirm the order.
An invalid CONFIG changes nothing. With no first header word, the kernel waits.

## results.md
Write results.md with these sections:
- Interface: the command and response layouts, how values pack into words,
  the status registers and the error codes.
- Design: the loop structure, where state is kept, and how the throughput
  target is reached.
- Targets: each target above with the required value, the measured value,
  PASS/FAIL and the file it came from (co-simulation for timing; synthesis
  for clock, II and resources).  Always report the latency and throughput
  from co-simulation and the estimated clock and resources from synthesis,
  writing "no target" where this prompt sets none.
- Verification: the model's check against the hand-computed examples and the
  reference; then one row per scenario saying whether the model, C simulation
  and co-simulation agree, and for each error scenario the status it set and
  whether the fresh activation after it passed. Name the source file of each.
- Assumptions: every place this prompt was silent or ambiguous and what you
  chose, apart from interface details already given under Interface.
- Open Items: questions you could not settle, and anything that failed or was
  not done, or "None".
- Run History: one row per run, with the prompt version, what was built or
  changed, and what passed, so that a later run can continue from here.

Every number and PASS/FAIL in Targets and Verification names the file it came
from (a log, a comparison output or a synthesis report), and that file stays in
this folder to be committed: a reviewer opens them to check results.md.

## Revision history
| Version | Change | Why |
| --- | --- | --- |
| 1 | First version | |
| 2 | Commands and valid values section | Prompt gave no command list, so run 1 would have guessed them, run 1 built this list, its fix after llm grader asks for it |
| 3 | All scenarios in every check; error codes 1 to 7 | Run 1 Open Items |
| 4 | DATA loops nsamp times and no response on sample TLAST errors; new CONFIG and added two error tests | Run 2 took 8,763 cycles for 1-sample DATA, sent a header before errors 6 and 7 and reused CONFIG values |
| 5 | DATA loop bound fixed | Run 3 still looped to 4096 |
| 6 | Invalid CONFIG and no first header word settled | Run 4 Assumptions, I kept its choices |
| 7 | Same bin throughput of 0.5 samples per clock is now accepted | Run 4 achieved II=2 rather than the required II=1, and the prompt now records the accepted throughput |