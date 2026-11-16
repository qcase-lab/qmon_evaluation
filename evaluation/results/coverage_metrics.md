## RQ1/RQ2 coverage metrics

310 MQT Bench circuits (42 families, 2–14 qubits), Qmax = 24. 
Source: the authors'
per-circuit results from the paper (`results/core/coverage.csv`), 
Produced by `evaluation/src/coverage_rq12_metrics.py`.

### Definitions

### NOTE FOR LATER: try qmax > 28 with regards to deployment coverage 

| Term / metric                   | RQ  | Formula (per circuit unless stated)                                                   |
| :------------------------------ | :-: | :------------------------------------------------------------------------------------ |
| Gate–qubit location             |  –  | A gate paired with one qubit it acts on (1-qubit gate = 1, 2-qubit gate = 2)          |
| Numerical candidate             | RQ1 | Location where Alg 1 finds the qubit separable (second Schmidt amplitude ≤ 1e-12) |
| Deployed checkpoint             | RQ2 | Candidate instrumented in a batch under Qmax = 24, plus free final reads              |
| Numerical-candidate rate        | RQ1 | candidates / locations                                                                |
| Pooled numerical-candidate rate | RQ1 | Σ candidates / Σ locations, over all 310 circuits                                     |
| Deployed location coverage      | RQ2 | deployed checkpoints / locations                                                      |
| Deployed gate coverage          | RQ2 | gates with ≥ 1 deployed checkpoint / gates                                            |
| Qubit coverage                  | RQ2 | qubits with ≥ 1 deployed checkpoint / qubits                                          |
| Normalized depth reach          | RQ2 | ASAP layer of the deepest deployed checkpoint / circuit depth (in layers)             |
| Full qubit coverage             | RQ2 | Every qubit in the circuit has ≥ 1 deployed checkpoint (counted over circuits)        |

### Distribution over the 310 circuits

| Metric                     |   Mean |   Min |    P25 | Median |     P75 |     Max |  Paper |
| :------------------------- | -----: | ----: | -----: | -----: | ------: | ------: | -----: |
| Numerical-candidate rate   | 42.05% | 0.45% |  8.62% | 23.19% | 100.00% | 100.00% |      – |
| Deployed location coverage | 40.68% | 0.45% |  8.08% | 22.55% | 100.00% | 100.00% | 44.54% |
| Deployed gate coverage     | 44.54% | 0.84% | 12.50% | 30.43% | 100.00% | 100.00% |      – |
| Qubit coverage             | 89.75% | 7.14% | 100.00% | 100.00% | 100.00% | 100.00% | 89.75% |
| Normalized depth reach     | 48.57% | 1.06% |  5.88% | 25.00% | 100.00% | 100.00% | 48.57% |



### Corpus totals

| Quantity | Value |
| --- | --- |
| Circuits / families / total qubits | 310 / 42 / 2,490 |
| Gates | 36,255 |
| Gate–qubit locations | 56,386 |
| Numerical candidates | 22,332 (pooled rate 39.61%; paper 39.61%) |
| Deployed checkpoints | 20,464 = 19,721 instrumented + 743 final reads (36.29% of locations, pooled) |
| Candidates not deployed (qubit budget) | 1,868 in 1,489 dropped groups, across 17 circuits |
| Fully deployable circuits (all candidates deployed) | 293 / 310 (94.52%; paper Table VI 94.52%) |
| Gates with ≥ 1 deployed checkpoint | 14,978 (41.31% of gates, pooled) |
| Circuits with full qubit coverage | 254 / 310 (81.94%; paper 254 / 310) |
| Circuits with 100% deployed location coverage | 80 / 310 |
| Batches (Qmax = 24) | 7,215 in total; median 1 per circuit; max 853 |

Distributions are bimodal: at least a quarter of circuits reach 100% on every metric
(P75 = 100%), while the median circuit's deployed location coverage is 22.55%.