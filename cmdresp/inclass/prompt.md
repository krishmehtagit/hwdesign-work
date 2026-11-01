We are building a clamp and count

Build a Vitis HLS kernel with a bit exact Python model in the folder that I have attached. For example, follow the waveflow stream inbound example from this link https://sdrangan.github.io/waveflow/docs/examples/stream_inband/ , and you need to use the command response pattern from this link https://sdrangan.github.io/hwdesign/docs/labs/cmdresp/pattern.html. Follow the pattern for configuration in a command and not the AXI light, right?


I want to run the Python model and see simulation while checking that they agree bit for bit. Once the C simulation passes, not synthesize or code similar, just write the results.md. I've described it below.

All files are on this local folder. Do not commit. For the Python model, run it on this Mac locally on the virtual environment.
/Users/krishmehta/Desktop/6463/.venv/bin/python

For the C simulation, because Vitis is not on this Mac, I usually run it on the ECS servers. The following is information that you need.
ecs03.poly.edu with user km6152
copy the folder cmdresp_inclass on the server and run ssh km6152@ecs03.poly.edu bash -s with a herodoc
activate the .venv and export WAVEFLOW_VITIS_PATH=/eda/xilinx/2026.1/Vitis/bin/vitis-run
copy the output of the C simulation and logs back to this folder for comparision.

Operation All samples and parameters are 32-bit floats. For each sample x, we check if x is less than lo, Then y is equal to hello, which is clipped. If x is greater than hi, then y is equal to hi, which is clipped. If both are false, then y is equal to x, where nothing is clipped. The clipped count is an unsigned 32-bit integer that carries across the data commands Config replaces lo and hi and sets the count to 0.

Commands
CONFIG(lo, hi): no response
DATA(nsamp): followed by nsamp samples; returns nsamp clamped samples
COUNT: returns the count in its response header
END: no response; the kernel returns
lo and hi must not be NaN, and lo <= hi. nsamp is from 1 to 1024.

errors
report errors and handle them as I listed below. Check in this particular order and this particular order only. So the whenever the first one is applied, First, check for unknown commands or check for data or count before any config in this activation, or check if there is an invalid LO, HI or NSAMP. If any of these three errors occur, send nothing for that command. And then you can check for tlast, like early tlast on a data sample before any sample NSAMP. If this is the case, then write the sample that carried the tlast and the last output word with the tlast, or check if the tlast is missing. For this error, you can just write all NSAMP output samples with tlast on the last.

verification
check the Python model against hand computed examples and run this in particular order.
CONFIG(-1.0, 1.0), then DATA [-2.0, 0.5, 3.0] gives [-1.0, 0.5, 1.0], and COUNT returns 2.
CONFIG(0.0, 2.0), then COUNT returns 0.

also test
nsamp = 1 and nsamp = 1024
lo == hi, NaN and -0.0
each error in its own activation, followed by a fresh activation with fresh streams that must pass

results.md
Include a table of every scenario with PASS or FAIL, and a list of every place this prompt was silent or ambiguous and what you chose.
