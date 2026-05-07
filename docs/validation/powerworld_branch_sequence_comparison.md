# PowerWorld Branch Sequence Screenshot Comparison

This note records the test using branch zero-sequence values transcribed from the PowerWorld Sequence Data -> Branches screenshot.

Case file:

```text
data/raw/ieee14/case14_powerworld_branch_sequence.m
```

## Entered Data

The case includes visible PowerWorld columns:

```text
Seq. R0
Seq. X0
Seq. C0
```

Generator sequence values remain placeholders because the visible PowerWorld generator screenshot did not show populated sequence resistance/reactance cells.

## Bus 1 SLG Result

Fault settings:

```text
Fault type: SLG / LG
Fault bus: 1
Fault impedance: 0 + j0 pu
Prefault solver: NR
```

| Case | Include line charging | Ia magnitude (pu) | Ia angle (deg) | |Z0+Z1+Z2+3Zf| (pu) |
| --- | --- | ---: | ---: | ---: |
| Default GridSolver assumptions | No | 12.009480 | -85.3013 | 0.264791 |
| PowerWorld branch sequence | No | 11.993331 | -85.2649 | 0.265147 |
| PowerWorld branch sequence | Yes | 11.891570 | -85.2798 | 0.267416 |
| PowerWorld screenshot target | N/A | 3.628000 | -78.66 | approx. 0.8765 |

## Interpretation

The visible PowerWorld branch sequence data only changes the bus-1 SLG result slightly. This means the main mismatch is probably not the visible branch `R0/X0/C0` table by itself.

The missing/high-impact items are likely:

- generator sequence reactance/resistance values or PowerWorld default generator fault parameters
- transformer zero-sequence grounding/path columns to the right of the visible screenshot
- fault-analysis options controlling generator modeling and sequence defaults
