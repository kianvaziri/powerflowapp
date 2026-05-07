"""Core data structures for parser and network-model layers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Bus:
    bus_i: int
    bus_type: int
    pd: float
    qd: float
    gs: float
    bs: float
    area: int
    vm: float
    va: float
    base_kv: float
    zone: int
    vmax: float
    vmin: float
    seq_g1: float = 0.0
    seq_b1: float = 0.0
    seq_g2: float = 0.0
    seq_b2: float = 0.0
    seq_g0: float = 0.0
    seq_b0: float = 0.0


@dataclass(frozen=True)
class Generator:
    bus: int
    pg: float
    qg: float
    qmax: float
    qmin: float
    vg: float
    mbase: float
    status: int
    pmax: float
    pmin: float
    r1: float | None = None
    x1: float | None = None
    r2: float | None = None
    x2: float | None = None
    r0: float | None = None
    x0: float | None = None
    rn: float = 0.0
    xn: float = 0.0


@dataclass(frozen=True)
class Branch:
    fbus: int
    tbus: int
    r: float
    x: float
    b: float
    ratio: float
    angle: float
    status: int
    r2: float | None = None
    x2: float | None = None
    b2: float | None = None
    r0: float | None = None
    x0: float | None = None
    b0: float | None = None
    zero_sequence_status: int = 1


@dataclass(frozen=True)
class PowerSystemCase:
    base_mva: float
    buses: list[Bus]
    generators: list[Generator]
    branches: list[Branch]
