"""clamp_count.py -- the streaming polynomial accelerator, written hook-first.

What is in this file, in the order a reader needs it:

1. **Schemas** -- the command header (which carries the coefficients), the response header
   and the error codes.  Waveflow generates their C++ headers and serializers; nothing packs
   words by hand.
2. **The bit-exact model** -- pure functions with no simulator in them:
   :func:`clamp_count_eval` (the arithmetic, float32 in the C++ operation order) and
   :func:`clamp_count_stream_model` (the whole protocol over a stream of bursts, TLAST rules
   included).  This is what a system simulation calls, and what the C++ kernel is
   checked against, byte for byte.
3. **The module** -- :class:`ClampCountAccel` declares the ports and the register map (status
   only) and names its kernel body (``cpp_body = "body"``).  Waveflow generates the
   kernel's boundary (the prototype and every interface pragma) and a single call to the
   hand-written C++ body, ``clamp_count_body_impl.tpp``.  The Python :meth:`ClampCountAccel.body` is the same kernel for
   pysim: a thin port wrapper around :func:`clamp_count_eval`, plus a timing model.
4. **The pysim testbench** -- :class:`ClampCountTB` plays a scenario's stimulus file into the
   module, the same file the hand-written C++ testbench (``clamp_count_tb.cpp``) plays into the
   Vitis kernel.

The scenarios, their independently computed expected outputs, and the checker are in
``scenarios.py``; the build that runs everything is ``clamp_count_build.py``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import ClassVar

import numpy as np
import numpy.typing as npt

from waveflow.hw.arrayutils import array, read_array, write_array
from waveflow.hw.clock import Clock
from waveflow.hw.dataschema import DataArray, DataList, EnumField, FloatField, IntField
from waveflow.hw.hw_hostactivated import HostActivated
from waveflow.hw.hw_module import HwConst, HwParam
from waveflow.hw.interface import StreamIF, StreamIFMaster, StreamIFSlave
from waveflow.hw.irq import IrqIF, IrqIFSink
try:
    from waveflow.hw.timed_phase import TimedPhase
except ModuleNotFoundError:
    TimedPhase = None  # type: ignore[assignment,misc]
from waveflow.hw.memif import DirectMMIF, MMIFMaster
from waveflow.hw.regmap import (
    Bit,
    RegAccess,
    RegField,
    VitisRegMap,
    VitisRegMapMMIFSlave,
)
from waveflow.simulation.logger import Logger, NullLogger
from waveflow.simulation.simobj import ProcessGen, SimObj
from waveflow.simulation.simulation import Simulation
from waveflow.utils.burst_io import StreamBurst, read_bursts

# ---------------------------------------------------------------------------
# 1. Schemas
# ---------------------------------------------------------------------------

INCLUDE_DIR = "include"
WORD_BW_SUPPORTED = [32]
TxIdField = IntField.specialize(bitwidth=16, signed=False)
NsampField = IntField.specialize(bitwidth=16, signed=False)
OpcodeField = IntField.specialize(bitwidth=8, signed=False)
Float32 = FloatField.specialize(bitwidth=32, include_dir=INCLUDE_DIR)


class ClampCountError(IntEnum):
    """What the kernel reports in its ``error`` register when it halts."""
    NO_ERROR = 0
    TLAST_EARLY_SAMP_IN = 1   # TLAST arrived before the last sample word
    NO_TLAST_SAMP_IN = 2      # the last sample word had no TLAST
    UNKNOWN_COMMAND = 3
    NOT_CONFIGURED = 4
    BAD_PARAM = 5

ClampCountErrorField = EnumField.specialize(enum_type=ClampCountError)


class ClampCountCmdType(IntEnum):
    CONFIG = 0
    DATA = 1
    COUNT = 2
    END = 3


class ClampCountCmdHdr(DataList):
    """In-band command header; bounds apply only to CONFIG and nsamp only to DATA."""
    elements = {
        "cmd_type": {"schema": OpcodeField,      "description": "CONFIG, DATA, COUNT, END, or unknown"},
        "tx_id":    {"schema": TxIdField,        "description": "Command ID: echoed, or reported on error"},
        "nsamp":    {"schema": NsampField,       "description": "Sample count (0 for END)"},
        "lo":       {"schema": Float32,          "description": "Lower bound for CONFIG"},
        "hi":       {"schema": Float32,          "description": "Upper bound for CONFIG"},
    }


class ClampCountRespHdr(DataList):
    """Response header: DATA echoes tx_id; COUNT also returns the accumulated count."""
    elements = {
        "tx_id": {"schema": TxIdField, "description": "Echo of the transaction ID"},
        "count": {"schema": IntField.specialize(bitwidth=32, signed=False), "description": "Clip count for COUNT; zero for DATA"},
    }


SCHEMA_CLASSES = [
    ClampCountErrorField,
    ClampCountCmdHdr,
    ClampCountRespHdr,
]

# ---------------------------------------------------------------------------
# 2. The bit-exact model (pure functions)
# ---------------------------------------------------------------------------


def clamp_count_eval(lo: np.float32, hi: np.float32, x: npt.ArrayLike) -> tuple[npt.NDArray[np.float32], int]:
    """Clamp float32 samples using ``x < lo`` then ``x > hi``; NaNs pass through unchanged."""
    xs = np.asarray(x, dtype=np.float32)
    y = xs.copy()
    clipped = 0
    for index, value in enumerate(xs):
        if value < lo:
            y[index] = lo
            clipped += 1
        elif value > hi:
            y[index] = hi
            clipped += 1
    return y, clipped


@dataclass
class ClampCountStreamResult:
    """What the kernel does to one stream: its output bursts and its final register status."""

    out: list[StreamBurst]
    halted: int = 0
    error: int = int(ClampCountError.NO_ERROR)
    tx_id: int = 0

    def status(self) -> dict[str, int]:
        return {"halted": self.halted, "error": self.error, "tx_id": self.tx_id}


def samples_per_word(word_bw: int) -> int:
    """float32 samples in one stream word: 1 at 32 bits, 2 at 64."""
    return word_bw // 32


def clamp_count_stream_model(bursts: list[StreamBurst], word_bw: int = 32) -> ClampCountStreamResult:
    """Pure command-stream implementation, matching the C++ body word for word."""
    if word_bw != 32:
        raise ValueError("clamp_count supports 32-bit stream words")
    words = [(int(word), index + 1 == len(burst.words) and burst.tlast)
             for burst in bursts for index, word in enumerate(np.asarray(burst.words, dtype=np.uint64))]
    header_words = ClampCountCmdHdr().serialize(word_bw=word_bw).size
    output: list[StreamBurst] = []
    result = ClampCountStreamResult(out=output)
    position, configured, count = 0, False, 0
    lo = hi = np.float32(0.0)

    def halt(error: ClampCountError, tx_id: int) -> ClampCountStreamResult:
        result.halted, result.error, result.tx_id = 1, int(error), int(tx_id)
        return result

    while True:
        if position + header_words > len(words):
            raise ValueError("the stimulus ends before a complete command header")
        header = ClampCountCmdHdr().deserialize([word for word, _ in words[position:position + header_words]], word_bw=word_bw)
        position += header_words
        opcode = int(header.cmd_type)
        if opcode not in {int(item) for item in ClampCountCmdType}:
            return halt(ClampCountError.UNKNOWN_COMMAND, header.tx_id)
        if opcode in (int(ClampCountCmdType.DATA), int(ClampCountCmdType.COUNT)) and not configured:
            return halt(ClampCountError.NOT_CONFIGURED, header.tx_id)
        if opcode == int(ClampCountCmdType.CONFIG):
            if np.isnan(header.lo) or np.isnan(header.hi) or header.lo > header.hi:
                return halt(ClampCountError.BAD_PARAM, header.tx_id)
            configured, lo, hi, count = True, np.float32(header.lo), np.float32(header.hi), 0
        elif opcode == int(ClampCountCmdType.DATA):
            if not 1 <= int(header.nsamp) <= 1024:
                return halt(ClampCountError.BAD_PARAM, header.tx_id)
            response = ClampCountRespHdr()
            response.tx_id, response.count = header.tx_id, 0
            output.append(StreamBurst(response.serialize(word_bw=word_bw)))
            samples: list[np.float32] = []
            early = False
            for sample_index in range(int(header.nsamp)):
                if position >= len(words):
                    raise ValueError("the stimulus ends inside a DATA burst")
                word, last = words[position]
                position += 1
                sample = read_array([word], elem_type=Float32, word_bw=word_bw, shape=1).val[0]
                samples.append(sample)
                if last and sample_index + 1 < int(header.nsamp):
                    early = True
                    break
                missing = sample_index + 1 == int(header.nsamp) and not last
            y, clips = clamp_count_eval(lo, hi, np.asarray(samples, dtype=np.float32))
            output.append(StreamBurst(write_array(y, elem_type=Float32, word_bw=word_bw)))
            count = (count + clips) & 0xFFFFFFFF
            if early:
                return halt(ClampCountError.TLAST_EARLY_SAMP_IN, header.tx_id)
            if missing:
                return halt(ClampCountError.NO_TLAST_SAMP_IN, header.tx_id)
        elif opcode == int(ClampCountCmdType.COUNT):
            response = ClampCountRespHdr()
            response.tx_id, response.count = header.tx_id, count
            output.append(StreamBurst(response.serialize(word_bw=word_bw)))
        else:
            return result


# ---------------------------------------------------------------------------
# 3. The module: ports, register map, and the kernel body
# ---------------------------------------------------------------------------


@dataclass
class ClampCountAccel(HostActivated):
    """The polynomial accelerator: a body-only kernel.

    The module declares the ports and the register map and names its body.  Waveflow
    generates ``gen/clamp_count.hpp`` / ``gen/clamp_count.cpp`` -- the prototype, every interface pragma,
    and one call ``clamp_count_impl::body(s_in, m_out, halted, error, tx_id)`` -- and the whole
    kernel is the hand-written ``clamp_count_body_impl.tpp``.  The register map holds only status;
    its fields reach the body by reference, so it writes ``halted`` / ``error`` / ``tx_id``
    itself.  Everything the kernel computes with arrives on ``s_in`` (contract rule 2).

    ``param_supports`` adds a 64-bit variant: a second top, ``clamp_count_bw64``, calling the same
    templated body with two samples per word.
    """

    cpp_kernel_name: ClassVar[str | None] = "clamp_count"
    # The hook-wrapping namespace must differ from the kernel function name, or
    # `::clamp_count(...)` at the testbench call site is ambiguous.
    cpp_namespace:   ClassVar[str | None] = "clamp_count_impl"
    cpp_body:        ClassVar[str | None] = "body"
    param_supports:  ClassVar[dict | None] = None

    in_bw:        HwParam[int] = 32
    out_bw:       HwParam[int] = 32
    aximm_bw:     HwParam[int] = 32
    clk:          Clock = field(default_factory=lambda: Clock(freq=1e9))
    # The timing model's SEEDS (pysim only): the samples' first result proc_latency cycles after
    # their first word, then one word per proc_ii cycles.  They are the declared phases' starting
    # point (see __post_init__) until those are fitted against RTL; set by hand against cosim.
    # See docs/examples/stream_inband/05_cosim_timing.md.
    proc_ii:      int = 1
    proc_latency: int = 40
    logger:       Logger | NullLogger = field(default_factory=NullLogger)
    unroll_factor: int = 1

    def __post_init__(self) -> None:
        super().__post_init__()
        self.s_in  = StreamIFSlave( name=f'{self.name}_s_in',  sim=self.sim, bitwidth=self.in_bw)
        self.m_out = StreamIFMaster(name=f'{self.name}_m_out', sim=self.sim, bitwidth=self.out_bw)
        self.regmap = VitisRegMap({
            "halted": RegField(Bit,            RegAccess.R, description="1 = halted on error"),
            "error":  RegField(ClampCountErrorField, RegAccess.R, description="Error code (ClampCountError)"),
            "tx_id":  RegField(TxIdField,      RegAccess.R, description="tx_id of the failed command"),
        }, bitwidth=self.aximm_bw)
        self.s_lite = VitisRegMapMMIFSlave(
            name=f'{self.name}_s_lite', sim=self.sim, bitwidth=self.aximm_bw,
            regmap=self.regmap, on_start=self.on_start,
        )
        for ep in (self.s_in, self.m_out, self.s_lite):
            self.add_endpoint(ep)
        self._job: int = 0
        # The timed phases (plans/pipelined_ops.md), one per shape the body has:
        # * the response header after the command header -- sequential (Pattern 1);
        # * the samples -> results loop -- pipelined (Pattern 2): a latency from the first sample
        #   word to the first result word, then the results at the loop's rate.
        # The durations are the phases' models, in cycles; these numbers only seed them.  Fitted
        # parameters, per width, are loaded from calib/w<W>/<phase>/ when they have been filed there
        # (clamp_count_calibrate.py).
        cal = Path(__file__).resolve().parent / "calib" / f"w{int(self.in_bw)}"
        if TimedPhase is not None:
            self.hdr_phase = TimedPhase(
                "hdr", spans={"resp_time": (self.s_in.last, self.m_out.first)},
                seed={"resp_time": {"intercept": 0.0}}, calib_dir=cal / "hdr")
            self.samp_phase = TimedPhase(
                "samples", spans={"latency": (self.s_in.first, self.m_out.first),
                                  "fill_time": (self.m_out.first, self.m_out.last)},
                features=("nwords",),
                seed={"latency": {"intercept": float(self.proc_latency), "nwords": 0.0},
                      "fill_time": {"intercept": 0.0,
                                    "nwords": float(self.proc_ii) / self.unroll_factor}},
                calib_dir=cal / "samples")
            for phase in (self.hdr_phase, self.samp_phase):
                self.add_timing_phase(phase)

    def _halt(self, err: ClampCountError, tx_id: int) -> None:
        self.regmap.set("error", err)
        self.regmap.set("tx_id", tx_id)
        self.regmap.set("halted", 1)

    def _respond(self, wait, resp_hdr: "ClampCountRespHdr") -> ProcessGen[None]:
        """The response header: after the header phase's wait (*wait*, already taken), written."""
        yield wait
        yield from self.m_out.write(resp_hdr)

    def body(self) -> ProcessGen[None]:
        """The kernel for pysim: the port wrapper around :func:`clamp_count_eval`, plus timing.

        Ordinary Python -- this is never translated to C++.  It reads and writes the ports,
        calls the pure model for the arithmetic, and lets the declared phases model time: the
        response header follows the command header by ``resp_time``; the samples go through the
        pipelined phase, their results starting ``latency`` after the first sample word.
        """
        self.logger.log(event='proc_begin', job=self._job)
        configured, count = False, 0
        lo = hi = np.float32(0.0)
        for f in ("halted", "error", "tx_id"):          # rule 5: this run's status only
            self.regmap.set(f, 0)
        while True:
            cmd_hdr: ClampCountCmdHdr = yield from self.s_in.get_schema(ClampCountCmdHdr)
            opcode = int(cmd_hdr.cmd_type)
            if opcode not in {int(item) for item in ClampCountCmdType}:
                self._halt(ClampCountError.UNKNOWN_COMMAND, cmd_hdr.tx_id)
                return
            if opcode in (int(ClampCountCmdType.DATA), int(ClampCountCmdType.COUNT)) and not configured:
                self._halt(ClampCountError.NOT_CONFIGURED, cmd_hdr.tx_id)
                return
            if opcode == int(ClampCountCmdType.CONFIG):
                if np.isnan(cmd_hdr.lo) or np.isnan(cmd_hdr.hi) or cmd_hdr.lo > cmd_hdr.hi:
                    self._halt(ClampCountError.BAD_PARAM, cmd_hdr.tx_id)
                    return
                configured, lo, hi, count = True, np.float32(cmd_hdr.lo), np.float32(cmd_hdr.hi), 0
                continue
            if opcode == int(ClampCountCmdType.END):
                self.logger.log(event='proc_end', job=self._job)
                return
            if opcode == int(ClampCountCmdType.COUNT):
                resp_hdr = ClampCountRespHdr()
                resp_hdr.tx_id, resp_hdr.count = cmd_hdr.tx_id, count
                yield from self.m_out.write(resp_hdr)
                continue
            if not 1 <= int(cmd_hdr.nsamp) <= 1024:
                self._halt(ClampCountError.BAD_PARAM, cmd_hdr.tx_id)
                return
            resp_hdr = ClampCountRespHdr()
            resp_hdr.tx_id, resp_hdr.count = cmd_hdr.tx_id, 0
            # The response goes out while the samples come in, as the RTL overlaps them: the header
            # phase's wait is taken now (its span starts at this header's last beat), and the
            # response is written by a process of its own while the sample pipeline begins.
            resp = self.env.process(self._respond(self.hdr_phase.timeout(), resp_hdr))
            # The samples: get_array(Float32, nsamp) and the results' write, deferred, and the pure
            # function between them.  compute gets the samples that arrived: a burst that ends early
            # at TLAST is shorter, and its results still go out as one burst, closed (rule 6).
            load = self.s_in.get_array(Float32, cmd_hdr.nsamp)
            store = self.m_out.write_array(Float32, cmd_hdr.nsamp)

            def compute(x):
                nonlocal count
                y, clips = clamp_count_eval(lo, hi, x.val)
                count = (count + clips) & 0xFFFFFFFF
                return array(Float32, y)

            r = yield from self.samp_phase.pipeline(compute, load=load, store=store,
                                                    nwords=load.nwords())
            yield resp
            self._job += 1

            if len(r.y.val) < cmd_hdr.nsamp:    # TLAST came early: halt, read nothing more
                self._halt(ClampCountError.TLAST_EARLY_SAMP_IN, cmd_hdr.tx_id)
                self.logger.log(event='proc_end', job=self._job)
                return


# ---------------------------------------------------------------------------
# 4. The pysim testbench
# ---------------------------------------------------------------------------

#: What the status registers hold before a run: what a kernel that forgot to clear its
#: status (rule 5) would leave behind.  Both testbenches poison them, so that kernel fails.
POISONED_STATUS = {"halted": 1, "error": int(ClampCountError.NO_TLAST_SAMP_IN), "tx_id": 0xFFFF}


@dataclass(kw_only=True)
class ClampCountTB(SimObj):
    """Plays a scenario's stimulus file into :class:`ClampCountAccel` and records the response.

    The stimulus is the same burst bundle the C++ testbench plays (``<scenario>/in``).  One
    kernel run: the testbench poisons the status registers, starts the kernel and sleeps
    until its ``ap_done`` interrupt, while two other processes push the stimulus and collect
    the response -- pushing everything first could deadlock, because the kernel blocks writing
    output nobody is reading yet.  Then it reads the status.  After an error, whatever the
    kernel left unread stays in the input channel and the scenario ends: that is the host
    resetting the stream path (rule 7).  A pysim stream cannot omit TLAST, so the
    missing-TLAST scenario runs only through the pure model and the C++ kernel.
    """

    stimulus:  Path
    n_out:     int                       # output bursts to collect
    word_bw:   int = 32
    base_addr: int = 0x0

    def __post_init__(self) -> None:
        super().__post_init__()
        self.m_in   = StreamIFMaster(name=f'{self.name}_m_in',   sim=self.sim, bitwidth=self.word_bw)
        self.s_out  = StreamIFSlave( name=f'{self.name}_s_out',  sim=self.sim, bitwidth=self.word_bw)
        self.m_lite = MMIFMaster(    name=f'{self.name}_m_lite', sim=self.sim, bitwidth=32)
        self.irq    = IrqIFSink(     name=f'{self.name}_irq',    sim=self.sim)
        self.out: list[StreamBurst] = []
        self.status: dict[str, int] = {}
        self._regmap_ref: VitisRegMap | None = None

    def run_proc(self) -> ProcessGen[None]:
        for f, v in POISONED_STATUS.items():     # left over from "a previous run"
            self._regmap().set(f, v)
        rm = self._regmap().bind_master(self.m_lite, base_addr=self.base_addr)
        reader = self.env.process(self._read_all())
        self.env.process(self._write_all())
        yield from rm.run(self.irq)              # enable ap_done irq, start, sleep until done
        yield reader
        for f in ("halted", "error", "tx_id"):
            self.status[f] = int((yield from rm.get(f)))    # int: written as JSON

    def _write_all(self) -> ProcessGen[None]:
        word_t = np.uint32 if self.word_bw <= 32 else np.uint64
        for b in read_bursts(self.stimulus):
            yield from self.m_in.write(np.asarray(b.words, dtype=word_t))

    def _read_all(self) -> ProcessGen[None]:
        for _ in range(self.n_out):
            words = yield from self.s_out.get()
            self.out.append(StreamBurst(np.asarray(words, dtype=np.uint64), True))

    def _regmap(self) -> VitisRegMap:
        if self._regmap_ref is None:
            raise RuntimeError("ClampCountTB._regmap_ref is unset; call connect() before run_sim().")
        return self._regmap_ref


def connect(sim: Simulation, tb: ClampCountTB, accel: ClampCountAccel, clk: Clock) -> None:
    """Wire the testbench to the accelerator: two streams, AXI-Lite, and the interrupt line."""
    in_stream  = StreamIF(sim=sim, clk=clk)
    out_stream = StreamIF(sim=sim, clk=clk)
    lite_link  = DirectMMIF(sim=sim, clk=clk, byte_addressable=True)
    irq        = IrqIF(name=f'{accel.name}_irq', sim=sim)
    in_stream.bind( "master", tb.m_in)
    in_stream.bind( "slave",  accel.s_in)
    out_stream.bind("master", accel.m_out)
    out_stream.bind("slave",  tb.s_out)
    lite_link.bind( "master", tb.m_lite)
    lite_link.bind( "slave",  accel.s_lite)
    irq.bind("source", accel.s_lite.interrupt())
    irq.bind("sink",   tb.irq)
    tb._regmap_ref = accel.regmap
