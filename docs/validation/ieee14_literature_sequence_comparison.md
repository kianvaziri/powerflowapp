# IEEE 14 Literature Sequence Data Comparison

This note records the first test using literature-based sequence data entered in:

```text
data/raw/ieee14/case14_literature_sequence.m
```

## Source Used

The generator and transformer sequence values were entered from the sequence-data tables in:

```text
Junaidi et al., "Modelling and Simulation of Symmetrical and Unsymmetrical Faults on 14 Bus IEEE-Power Systems", JATIT, 2021.
```

The paper's transmission-line table provides positive-sequence line data. For ordinary transmission lines where explicit zero-sequence values were not available, GridSolver keeps the placeholder assumption:

```text
Z2 = Z1
Z0 = 2.5 * Z1
```

## Bus 1 SLG Comparison

Fault settings:

```text
Fault type: SLG / LG
Fault bus: 1
Fault impedance: 0 + j0 pu
Prefault solver: NR
Tolerance: 1e-10
```

| Case | Ia magnitude (pu) | Ia angle (deg) | |Z0+Z1+Z2+3Zf| (pu) |
| --- | ---: | ---: | ---: |
| Default GridSolver assumptions | 12.009480 | -85.3013 | 0.264791 |
| PowerWorld screenshot target | 3.628000 | -78.66 | approx. 0.8765 |
| Literature sequence case | 163.922290 | -81.1843 | 0.019399 |

## Interpretation

The literature sequence case does not match the PowerWorld screenshot. It moves the result farther away because the entered generator sequence reactances are very small, which greatly reduces the Thevenin sequence denominator at bus 1.

This suggests the literature data is not on the same modeling basis as the PowerWorld case being used for comparison, or the published dataset is incomplete for this specific PowerWorld fault-study model.

The next best comparison path is still to export/copy the actual PowerWorld Sequence Data tables for generators, branches, transformers, and bus/load/shunt sequence records.
