# PowerWorld Sequence Data Entry Guide

This guide explains how to enter PowerWorld sequence data into GridSolver so fault-analysis results can be compared meaningfully.

## Why This Matters

For a single-line-to-ground fault, the method in the course notes gives:

```text
I0 = I1 = I2 = Ea / (Z0 + Z1 + Z2 + 3Zf)
Ia = 3I1
```

So equal sequence currents are expected for an A-phase SLG fault. If `Ia` is too high, the likely cause is that the denominator `Z0 + Z1 + Z2 + 3Zf` is too small. That denominator depends directly on generator, branch, transformer, grounding, load, and shunt sequence data.

## Template File

Use this file as the starting point:

```text
data/raw/ieee14/case14_powerworld_sequence_template.m
```

The template is valid MATPOWER-style input, but its sequence values are placeholders. Replace them with PowerWorld values before using it for validation. After editing, either select the edited file with the UI upload control or replace the bundled template file with your completed version.

## Generator Sequence Data

GridSolver section:

```matlab
%% bus r1 x1 r2 x2 r0 x0 rn xn
mpc.gen_seq = [
    1 0.00000 0.20000 0.00000 0.20000 0.00000 0.20000 0.00000 0.00000;
];
```

Copy from PowerWorld Sequence Data -> Generators or generator fault parameters:

| GridSolver column | Meaning |
| --- | --- |
| `bus` | generator bus number |
| `r1`, `x1` | positive-sequence generator resistance/reactance |
| `r2`, `x2` | negative-sequence generator resistance/reactance |
| `r0`, `x0` | zero-sequence generator resistance/reactance |
| `rn`, `xn` | generator neutral grounding resistance/reactance |

Keep the UI option `Generator sequence data uses generator MVA base` enabled if the PowerWorld values are on generator MVA base. Disable it only if the values have already been converted to the system base.

## Branch And Transformer Sequence Data

GridSolver section:

```matlab
%% fbus tbus r2 x2 b2 r0 x0 b0 zero_sequence_status
mpc.branch_seq = [
    1 2 0.01938 0.05917 0.05280 0.04845 0.14793 0.00000 1;
];
```

Copy from PowerWorld Sequence Data -> Branches and transformer sequence records:

| GridSolver column | Meaning |
| --- | --- |
| `fbus`, `tbus` | branch terminal bus numbers |
| `r2`, `x2`, `b2` | negative-sequence branch data |
| `r0`, `x0`, `b0` | zero-sequence branch data |
| `zero_sequence_status` | `1` to include the zero-sequence path, `0` to block/open it |

For transmission lines, `Z2` is often equal to `Z1`, but `Z0` is usually different. For transformers, zero-sequence behavior depends on winding connection and grounding. This is one of the most common reasons GridSolver and PowerWorld disagree.

## Bus/Load/Shunt Sequence Data

GridSolver section:

```matlab
%% bus g1 b1 g2 b2 g0 b0
mpc.bus_seq = [
    1 0.00000 0.00000 0.00000 0.00000 0.00000 0.00000;
];
```

Use this only if PowerWorld has explicit sequence load or shunt admittance records you want to model. Values are per-unit admittance on the system base.

## Validation Target

For the PowerWorld screenshot at bus 1 SLG fault:

```text
PowerWorld If magnitude: 3.628 pu
PowerWorld If angle:    -78.66 deg
```

Because the prefault bus-1 voltage is about `1.06 pu`, the expected denominator magnitude is approximately:

```text
|Z0 + Z1 + Z2 + 3Zf| = 3 * 1.06 / 3.628 = 0.8765 pu
```

After entering real sequence data, compare GridSolver's Fault Diagnostics table against PowerWorld:

```text
Z0_th
Z1_th
Z2_th
SLG denominator Z0+Z1+Z2+3Zf
```

If the diagnostic denominator is still near the old placeholder value, the PowerWorld sequence data has not been fully represented yet.
