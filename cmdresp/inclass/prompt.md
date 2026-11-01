We are building a clamp and count

Build a Vitis HLS kernel with a bit exact Python model in the folder that I have attached. For example, follow the waveflow stream inband example from this link https://sdrangan.github.io/waveflow/docs/examples/stream_inband/ , and you need to use the command response pattern from this link https://sdrangan.github.io/hwdesign/docs/labs/cmdresp/pattern.html. Follow the pattern for configuration in a command and not the AXI light


I want to run the Python model and C simulation while checking that they agree bit for bit. Once the C simulation passes, no synthesis or cosimulation, just write the results.md. I've described it below.

All files are on this local folder. Do not commit. For the Python model, run it on this Mac locally on the virtual environment.
/Users/krishmehta/Desktop/6463/.venv/bin/python

For the C simulation, because Vitis is not on this Mac, I usually run it on the ECS servers. The following is information that you need.
ecs03.poly.edu with user km6152
activate ~/ECE_6463/.venv and export WAVEFLOW_VITIS_PATH=/eda/xilinx/2026.1/Vitis/bin/vitis-run
activate the .venv and export WAVEFLOW_VITIS_PATH=/eda/xilinx/2026.1/Vitis/bin/vitis-run
copy the output of the C simulation and logs back to this folder for comparision.

Operation All samples and parameters are 32-bit floats. For each sample x, we check if x is less than lo, Then y is equal to lo, which is clipped. If x is greater than hi, then y is equal to hi, which is clipped. If both are false, then y is equal to x, where nothing is clipped. The clipped count is an unsigned 32-bit integer that carries across the data commands Config replaces lo and hi and sets the count to 0.
Use the exactly same comparison in this order. a NaN sample will fail both. So this will make it pass through with its bits unchanged and not clipped. The count will wrap to modulo 2^32

Commands
CONFIG(lo, hi): no response
DATA(nsamp): followed by nsamp samples; returns nsamp clamped samples
COUNT: returns the count in its response header
END: no response; the kernel returns
lo and hi must not be NaN, and lo <= hi. nsamp is from 1 to 1024.

errors
On every error, the kernel will set the status registers: halted, error code, offending TXID. Close any output burst which started with TLAST and return at once without reading more inputs.
After this, check this in this particular order. Whichever these the first that applies wins.
Number one is unknown command. Number two is data or count before config in this activation. Number three is invalid, lo, hi, or nsamp. If the error is any one of these, then no output burst was started. So send nothing for this command. Number four, check if the TLAST was early. If that's the case, the sample that carried TLAST is the last one processed, and its output word carries the TLAST. Number five, if the TLAST is missing, then the TLAST error was detected at sample nsamp. So that sample's output word carries the TLAST.

verification
check the Python model against hand computed examples and run this in particular order.
CONFIG(-1.0, 1.0), then DATA [-2.0, 0.5, 3.0] gives [-1.0, 0.5, 1.0], and COUNT returns 2.
CONFIG(0.0, 2.0), then COUNT returns 0.

also test
nsamp = 1 and nsamp = 1024
lo == hi, NaN and -0.0
each error in its own activation, followed by a fresh activation with fresh streams that must pass

results.md
Include a table of every scenario with a pass or fail, which shows that Python model and C simulation agrees for bit by bit. Include the error scenarios and the fresh activations after them. For each result, name the log or output file it came from and keep the file in this folder. Also, list every place this prompt was silent for or ambiguous and what you chose after that.
