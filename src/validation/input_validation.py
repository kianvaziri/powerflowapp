"""Data-validation utilities for UI workflow checks."""

from __future__ import annotations

from dataclasses import dataclass

from src.models import PowerSystemCase

BUS_TYPE_SLACK = 3


@dataclass(frozen=True)
class ValidationFinding:
    severity: str  # "error" or "warning"
    code: str
    message: str


def validate_case_data(case: PowerSystemCase) -> list[ValidationFinding]:
    """Validate parsed case data against UI workflow rules."""
    findings: list[ValidationFinding] = []

    bus_ids = [bus.bus_i for bus in case.buses]
    bus_set = set(bus_ids)

    if any(bus_id <= 0 for bus_id in bus_ids):
        findings.append(
            ValidationFinding(
                severity="error",
                code="BAD_BUS_NUMBER",
                message="Bus numbers must be positive integers.",
            )
        )

    if len(bus_ids) != len(bus_set):
        findings.append(
            ValidationFinding(
                severity="error",
                code="DUPLICATE_BUS_NUMBER",
                message="Duplicate bus numbers detected.",
            )
        )

    slack_count = sum(1 for bus in case.buses if bus.bus_type == BUS_TYPE_SLACK)
    if slack_count == 0:
        findings.append(
            ValidationFinding(
                severity="error",
                code="MISSING_SLACK_BUS",
                message="No slack bus found (type 3 required).",
            )
        )
    elif slack_count > 1:
        findings.append(
            ValidationFinding(
                severity="error",
                code="MULTIPLE_SLACK_BUSES",
                message=f"Multiple slack buses found ({slack_count}).",
            )
        )

    seen_branch_keys: set[tuple[int, int, float, float, float, float, float, int]] = set()
    for idx, branch in enumerate(case.branches):
        if branch.fbus not in bus_set or branch.tbus not in bus_set:
            findings.append(
                ValidationFinding(
                    severity="error",
                    code="BAD_BRANCH_BUS_REFERENCE",
                    message=f"Branch #{idx + 1} references unknown bus ({branch.fbus}->{branch.tbus}).",
                )
            )

        if abs(branch.r) < 1e-14 and abs(branch.x) < 1e-14:
            findings.append(
                ValidationFinding(
                    severity="error",
                    code="ZERO_BRANCH_IMPEDANCE",
                    message=f"Branch #{idx + 1} has zero impedance (r=0 and x=0).",
                )
            )

        if branch.ratio < 0.0:
            findings.append(
                ValidationFinding(
                    severity="error",
                    code="BAD_TAP_RATIO",
                    message=f"Branch #{idx + 1} has negative tap ratio ({branch.ratio}).",
                )
            )

        # Treat exact duplicate oriented lines as likely data mistakes for UI validation.
        oriented = (branch.fbus, branch.tbus)
        reverse = (branch.tbus, branch.fbus)
        branch_key = (
            min(oriented[0], oriented[1]),
            max(oriented[0], oriented[1]),
            round(branch.r, 12),
            round(branch.x, 12),
            round(branch.b, 12),
            round(branch.ratio, 12),
            round(branch.angle, 12),
            int(branch.status),
        )
        if branch_key in seen_branch_keys:
            findings.append(
                ValidationFinding(
                    severity="warning",
                    code="DUPLICATE_BRANCH",
                    message=(
                        f"Potential duplicate branch near #{idx + 1} ({oriented[0]}<->{oriented[1]})."
                    ),
                )
            )
        seen_branch_keys.add(branch_key)

    for idx, gen in enumerate(case.generators):
        if gen.bus not in bus_set:
            findings.append(
                ValidationFinding(
                    severity="error",
                    code="BAD_GENERATOR_BUS_REFERENCE",
                    message=f"Generator #{idx + 1} references unknown bus ({gen.bus}).",
                )
            )

        if gen.status not in (0, 1):
            findings.append(
                ValidationFinding(
                    severity="error",
                    code="BAD_GENERATOR_STATUS",
                    message=f"Generator #{idx + 1} has invalid status ({gen.status}).",
                )
            )

        if gen.pmin > gen.pmax:
            findings.append(
                ValidationFinding(
                    severity="error",
                    code="INCONSISTENT_P_LIMITS",
                    message=f"Generator #{idx + 1} has Pmin > Pmax.",
                )
            )

        if gen.qmin > gen.qmax:
            findings.append(
                ValidationFinding(
                    severity="error",
                    code="INCONSISTENT_Q_LIMITS",
                    message=f"Generator #{idx + 1} has Qmin > Qmax.",
                )
            )

        if gen.status == 0 and (abs(gen.pg) > 1e-10 or abs(gen.qg) > 1e-10):
            findings.append(
                ValidationFinding(
                    severity="warning",
                    code="OFFLINE_GENERATOR_NONZERO_OUTPUT",
                    message=f"Generator #{idx + 1} is offline but has nonzero Pg/Qg.",
                )
            )

    return findings


def has_validation_errors(findings: list[ValidationFinding]) -> bool:
    return any(item.severity == "error" for item in findings)
