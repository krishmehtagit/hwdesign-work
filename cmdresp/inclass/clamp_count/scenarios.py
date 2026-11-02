"""Frozen Stage 1 intents and independent expected results for clamp_count."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from clamp_count import (ClampCountCmdHdr, ClampCountCmdType, ClampCountError,
                         ClampCountRespHdr, Float32, clamp_count_eval)
from waveflow.hw.arrayutils import write_array
from waveflow.utils.burst_io import StreamBurst, read_bursts, write_bursts


@dataclass(frozen=True)
class Command:
    opcode: int
    tx_id: int
    nsamp: int = 0
    lo: np.float32 = np.float32(0.0)
    hi: np.float32 = np.float32(0.0)
    samples: tuple[float, ...] = ()
    sent: int | None = None
    tlast: bool = True

    @property
    def sent_samples(self) -> tuple[float, ...]:
        return self.samples if self.sent is None else self.samples[:self.sent]


@dataclass(frozen=True)
class Scenario:
    commands: tuple[Command, ...]


def _header(command: Command, word_bw: int) -> np.ndarray:
    header = ClampCountCmdHdr()
    header.cmd_type, header.tx_id, header.nsamp = command.opcode, command.tx_id, command.nsamp
    header.lo, header.hi = command.lo, command.hi
    return header.serialize(word_bw=word_bw)


def _samples(samples: tuple[float, ...], word_bw: int) -> np.ndarray:
    return write_array(np.asarray(samples, dtype=np.float32), elem_type=Float32, word_bw=word_bw)


def stimulus(scenario: Scenario, word_bw: int) -> list[StreamBurst]:
    bursts: list[StreamBurst] = []
    for command in scenario.commands:
        bursts.append(StreamBurst(_header(command, word_bw)))
        if command.opcode == ClampCountCmdType.DATA and command.sent_samples:
            bursts.append(StreamBurst(_samples(command.sent_samples, word_bw), command.tlast))
    return bursts


def expected(scenario: Scenario, word_bw: int) -> tuple[list[StreamBurst], dict[str, int]]:
    """Derive the contract result directly from typed intents, never from a stream model."""
    configured, lo, hi, count = False, np.float32(0.0), np.float32(0.0), 0
    out: list[StreamBurst] = []
    valid_opcodes = {int(item) for item in ClampCountCmdType}
    for command in scenario.commands:
        if command.opcode not in valid_opcodes:
            error = ClampCountError.UNKNOWN_COMMAND
        elif command.opcode in (ClampCountCmdType.DATA, ClampCountCmdType.COUNT) and not configured:
            error = ClampCountError.NOT_CONFIGURED
        elif command.opcode == ClampCountCmdType.CONFIG and (np.isnan(command.lo) or np.isnan(command.hi) or command.lo > command.hi):
            error = ClampCountError.BAD_PARAM
        elif command.opcode == ClampCountCmdType.DATA and not 1 <= command.nsamp <= 1024:
            error = ClampCountError.BAD_PARAM
        else:
            error = ClampCountError.NO_ERROR
        if error != ClampCountError.NO_ERROR:
            return out, {"halted": 1, "error": int(error), "tx_id": command.tx_id}
        if command.opcode == ClampCountCmdType.CONFIG:
            configured, lo, hi, count = True, command.lo, command.hi, 0
        elif command.opcode == ClampCountCmdType.DATA:
            response = ClampCountRespHdr()
            response.tx_id, response.count = command.tx_id, 0
            out.append(StreamBurst(response.serialize(word_bw=word_bw)))
            values = np.asarray(command.sent_samples, dtype=np.float32)
            y, clips = clamp_count_eval(lo, hi, values)
            out.append(StreamBurst(_samples(tuple(y), word_bw)))
            count = (count + clips) & 0xFFFFFFFF
            if len(values) < command.nsamp:
                return out, {"halted": 1, "error": int(ClampCountError.TLAST_EARLY_SAMP_IN), "tx_id": command.tx_id}
            if not command.tlast:
                return out, {"halted": 1, "error": int(ClampCountError.NO_TLAST_SAMP_IN), "tx_id": command.tx_id}
        elif command.opcode == ClampCountCmdType.COUNT:
            response = ClampCountRespHdr()
            response.tx_id, response.count = command.tx_id, count
            out.append(StreamBurst(response.serialize(word_bw=word_bw)))
        elif command.opcode == ClampCountCmdType.END:
            break
    return out, {"halted": 0, "error": 0, "tx_id": 0}


def scenarios() -> dict[str, Scenario]:
    config = Command(ClampCountCmdType.CONFIG, 1, lo=np.float32(-1.0), hi=np.float32(1.0))
    fresh = Scenario((config, Command(ClampCountCmdType.DATA, 2, 3, samples=(-2.0, 0.5, 3.0)), Command(ClampCountCmdType.COUNT, 3), Command(ClampCountCmdType.END, 4)))
    return {
        "worked_example": fresh,
        "reconfig_resets_count": Scenario((config, Command(ClampCountCmdType.DATA, 5, 1, samples=(-2.0,)), Command(ClampCountCmdType.CONFIG, 6, lo=np.float32(0.0), hi=np.float32(2.0)), Command(ClampCountCmdType.COUNT, 7), Command(ClampCountCmdType.END, 8))),
        "nsamp_1": Scenario((config, Command(ClampCountCmdType.DATA, 9, 1, samples=(2.0,)), Command(ClampCountCmdType.END, 10))),
        "nsamp_1024": Scenario((config, Command(ClampCountCmdType.DATA, 11, 1024, samples=tuple(np.linspace(-2, 2, 1024, dtype=np.float32))), Command(ClampCountCmdType.END, 12))),
        "equal_bounds_nan_negzero": Scenario((Command(ClampCountCmdType.CONFIG, 13, lo=np.float32(-0.0), hi=np.float32(-0.0)), Command(ClampCountCmdType.DATA, 14, 3, samples=(-1.0, float("nan"), 1.0)), Command(ClampCountCmdType.END, 15))),
        "unknown_command": Scenario((Command(255, 16),)),
        "fresh_after_unknown": fresh,
        "data_before_config": Scenario((Command(ClampCountCmdType.DATA, 17, 1, samples=(0.0,)),)),
        "fresh_after_data_before_config": fresh,
        "count_before_config": Scenario((Command(ClampCountCmdType.COUNT, 18),)),
        "fresh_after_count_before_config": fresh,
        "bad_config_nan": Scenario((Command(ClampCountCmdType.CONFIG, 19, lo=np.float32("nan"), hi=np.float32(1.0)),)),
        "fresh_after_bad_config": fresh,
        "bad_nsamp_zero": Scenario((config, Command(ClampCountCmdType.DATA, 20, 0),)),
        "fresh_after_bad_nsamp": fresh,
        "early_tlast": Scenario((config, Command(ClampCountCmdType.DATA, 21, 3, samples=(-2.0, 0.5, 3.0), sent=2), Command(ClampCountCmdType.END, 22))),
        "fresh_after_early_tlast": fresh,
        "missing_tlast": Scenario((config, Command(ClampCountCmdType.DATA, 23, 3, samples=(-2.0, 0.5, 3.0), tlast=False), Command(ClampCountCmdType.END, 24))),
        "fresh_after_missing_tlast": fresh,
    }


def write_scenarios(data_dir: Path, word_bw: int) -> list[str]:
    data_dir.mkdir(parents=True, exist_ok=True)
    names = []
    for name, scenario in scenarios().items():
        directory = data_dir / name
        write_bursts(stimulus(scenario, word_bw), directory / "in")
        response, status = expected(scenario, word_bw)
        write_bursts(response, directory / "expected")
        (directory / "expected_status.json").write_text(json.dumps(status) + "\n")
        names.append(name)
    (data_dir / "scenarios.txt").write_text("\n".join(names) + "\n")
    return names


def check(data_dir: Path, stage: str, names: list[str] | None = None) -> dict[str, list[str]]:
    names = names or (data_dir / "scenarios.txt").read_text().split()
    report: dict[str, list[str]] = {}
    for name in names:
        directory, problems = data_dir / name, []
        got_directory = directory / stage
        if not (got_directory / "words.bin").exists():
            report[name] = [f"no {stage} output"]
            continue
        wanted, got = read_bursts(directory / "expected"), read_bursts(got_directory)
        if len(wanted) != len(got):
            problems.append(f"{len(got)} bursts, expected {len(wanted)}")
        for index, (want, actual) in enumerate(zip(wanted, got)):
            if want.tlast != actual.tlast or not np.array_equal(want.words, actual.words):
                problems.append(f"burst {index} differs")
        status_path = got_directory / "status.json"
        if not status_path.exists() or json.loads(status_path.read_text()) != json.loads((directory / "expected_status.json").read_text()):
            problems.append("status differs")
        report[name] = problems
    return report
