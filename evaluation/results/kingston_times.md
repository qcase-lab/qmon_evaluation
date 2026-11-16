# RQ3 device-time estimates on FakeKingston

Full run, 2026-11-14. 238 RQ3 circuits, the authors' 2,860 non-equivalent mutants, stored noise-free detection outcomes (`rq3_mutant.pkl`, `rq3_falsealarm.pkl`).

## Setup

| Item | Value |
|---|---|
| Backend | FakeKingston (156-qubit Heron r2), calibration snapshot 2026-04-15 |
| Compiler | Qiskit 2.4.1 preset pass manager, optimization level 2, ALAP scheduling |
| Transpiler seeds | 1, 2, 3 (median reported) |
| Duration of one shot (D) | `QuantumCircuit.estimate_duration(backend.target)` after compiling |
| Time per run | T_run = O_job + S × (t_rep + t_init + D) |
| Shots per run (S) | 8,192 |
| Wait between shots (t_rep) | 250 µs (`default_rep_delay`) |
| Initial reset (t_init) | median reset duration in t   he target (about 2.3 µs) |
| Per-job overhead (O_job) | swept over 0, 2, 5 s (IBM's guide: about 2 s per sub-job) |
| Qmax | 24 |
| Methods timed | QMON, statistical assertion, Proq, Liu (MQT is classical: not timed) |

## Column meanings

| Column | Meaning |
|---|---|
| n | Number of items summarized (circuits, mutants or compiled circuits) |
| Mean | Average |
| Min / Max | Smallest / largest value |
| P25 / Median / P75 | 25th / 50th / 75th percentile (nearest rank) |
| IQR | P75 − P25 |

## Metric definitions

| Metric | Unit | Definition |
|---|---|---|
| Full-check time per circuit | s | Device time to check one circuit completely, one job per run. QMON: all B batches. Baselines: one run per checkpoint, K runs. |
| Full-check time, one job | s | Same check with all of a circuit's runs packed into one job (O_job paid once) |
| Time to detection, detected mutants | s | For each mutant a method caught: baselines, runs in ascending checkpoint order up to and including the first flagged one; QMON, all B batches (paper's protocol) |
| QMON early stop (UB) | s | QMON stops after the batch holding the first flagged checkpoint. Upper bound: the stored first flag is in gate order, not batch order. |
| Time spent on missed mutants | s | For each mutant a method missed: the full-check time |
| QMON / baseline ratio | – | Per circuit: QMON full-check time ÷ baseline full-check time (below 1 = QMON faster) |

---

## 1. Device-time estimates

### O_job = 0 s

| Metric | Method | n | Mean | Min | P25 | Median | P75 | IQR | Max |
|---|---|---|---|---|---|---|---|---|---|
| Full-check time per circuit (s) | qmon | 238 | 88.9 | 2.13 | 2.21 | 2.4 | 33.7 | 31.5 | 2,633 |
| Full-check time per circuit (s) | statistical | 238 | 205 | 6.26 | 18.8 | 43.9 | 189 | 170 | 3,888 |
| Full-check time per circuit (s) | proq | 238 | 206 | 6.26 | 18.8 | 43.9 | 189 | 170 | 3,909 |
| Full-check time per circuit (s) | liu | 238 | 205 | 6.26 | 18.8 | 43.9 | 189 | 170 | 3,891 |
| Full-check time, one job (s) | qmon | 238 | 88.9 | 2.13 | 2.21 | 2.4 | 33.7 | 31.5 | 2,633 |
| Full-check time, one job (s) | statistical | 238 | 205 | 6.26 | 18.8 | 43.9 | 189 | 170 | 3,888 |
| Full-check time, one job (s) | proq | 238 | 206 | 6.26 | 18.8 | 43.9 | 189 | 170 | 3,909 |
| Full-check time, one job (s) | liu | 238 | 205 | 6.26 | 18.8 | 43.9 | 189 | 170 | 3,891 |
| Time to detection, detected mutants (s) | qmon | 1,782 | 93.2 | 2.13 | 2.21 | 4.49 | 40.1 | 37.9 | 2,633 |
| Time to detection, detected mutants (s) | statistical | 1,928 | 105 | 2.09 | 6.26 | 20.9 | 90 | 83.7 | 3,755 |
| Time to detection, detected mutants (s) | proq | 2,031 | 96.8 | 2.09 | 8.34 | 18.8 | 69 | 60.6 | 3,742 |
| Time to detection, detected mutants (s) | liu | 2,036 | 96.5 | 2.09 | 6.26 | 18.8 | 69 | 62.8 | 3,726 |
| Time to detection, detected mutants (s) | qmon early stop (UB) | 1,782 | 42.5 | 2.13 | 2.21 | 2.34 | 7.23 | 5.02 | 2,363 |
| Time spent on missed mutants (s) | qmon | 1,078 | 62.6 | 2.13 | 2.2 | 2.28 | 4.49 | 2.29 | 1,870 |
| Time spent on missed mutants (s) | statistical | 932 | 124 | 6.26 | 12.5 | 18.8 | 45.9 | 33.3 | 1,639 |
| Time spent on missed mutants (s) | proq | 829 | 129 | 6.26 | 12.5 | 16.7 | 25 | 12.5 | 1,634 |
| Time spent on missed mutants (s) | liu | 824 | 129 | 6.26 | 12.5 | 16.7 | 23.1 | 10.5 | 1,634 |

### O_job = 2 s

| Metric | Method | n | Mean | Min | P25 | Median | P75 | IQR | Max |
|---|---|---|---|---|---|---|---|---|---|
| Full-check time per circuit (s) | qmon | 238 | 149 | 4.13 | 4.21 | 4.4 | 61.7 | 57.4 | 4,339 |
| Full-check time per circuit (s) | statistical | 238 | 390 | 12.3 | 36.8 | 85.9 | 367 | 330 | 7,140 |
| Full-check time per circuit (s) | proq | 238 | 390 | 12.3 | 36.8 | 85.9 | 367 | 330 | 7,161 |
| Full-check time per circuit (s) | liu | 238 | 390 | 12.3 | 36.8 | 85.9 | 367 | 330 | 7,143 |
| Full-check time, one job (s) | qmon | 238 | 90.9 | 4.13 | 4.21 | 4.4 | 35.7 | 31.5 | 2,635 |
| Full-check time, one job (s) | statistical | 238 | 207 | 8.26 | 20.8 | 45.9 | 191 | 170 | 3,890 |
| Full-check time, one job (s) | proq | 238 | 208 | 8.26 | 20.8 | 45.9 | 191 | 170 | 3,911 |
| Full-check time, one job (s) | liu | 238 | 207 | 8.26 | 20.8 | 45.9 | 191 | 170 | 3,893 |
| Time to detection, detected mutants (s) | qmon | 1,782 | 159 | 4.13 | 4.21 | 8.49 | 70 | 65.8 | 4,339 |
| Time to detection, detected mutants (s) | statistical | 1,928 | 201 | 4.09 | 12.3 | 40.9 | 176 | 164 | 6,909 |
| Time to detection, detected mutants (s) | proq | 2,031 | 186 | 4.09 | 16.3 | 36.8 | 135 | 119 | 6,872 |
| Time to detection, detected mutants (s) | liu | 2,036 | 186 | 4.09 | 12.3 | 36.8 | 135 | 123 | 6,856 |
| Time to detection, detected mutants (s) | qmon early stop (UB) | 1,782 | 72.3 | 4.13 | 4.21 | 4.34 | 13.2 | 9.02 | 3,885 |
| Time spent on missed mutants (s) | qmon | 1,078 | 96.2 | 4.13 | 4.2 | 4.28 | 8.49 | 4.29 | 2,662 |
| Time spent on missed mutants (s) | statistical | 932 | 230 | 12.3 | 24.5 | 36.8 | 89.9 | 65.3 | 3,123 |
| Time spent on missed mutants (s) | proq | 829 | 238 | 12.3 | 24.5 | 32.7 | 49 | 24.5 | 3,118 |
| Time spent on missed mutants (s) | liu | 824 | 239 | 12.3 | 24.5 | 32.7 | 45.1 | 20.5 | 3,118 |

### O_job = 5 s

| Metric | Method | n | Mean | Min | P25 | Median | P75 | IQR | Max |
|---|---|---|---|---|---|---|---|---|---|
| Full-check time per circuit (s) | qmon | 238 | 239 | 7.13 | 7.21 | 7.4 | 104 | 96.4 | 6,898 |
| Full-check time per circuit (s) | statistical | 238 | 666 | 21.3 | 63.8 | 149 | 634 | 570 | 12,018 |
| Full-check time per circuit (s) | proq | 238 | 666 | 21.3 | 63.8 | 149 | 634 | 570 | 12,039 |
| Full-check time per circuit (s) | liu | 238 | 666 | 21.3 | 63.8 | 149 | 634 | 570 | 12,021 |
| Full-check time, one job (s) | qmon | 238 | 93.9 | 7.13 | 7.21 | 7.4 | 38.7 | 31.5 | 2,638 |
| Full-check time, one job (s) | statistical | 238 | 210 | 11.3 | 23.8 | 48.9 | 194 | 170 | 3,893 |
| Full-check time, one job (s) | proq | 238 | 211 | 11.3 | 23.8 | 48.9 | 194 | 170 | 3,914 |
| Full-check time, one job (s) | liu | 238 | 210 | 11.3 | 23.8 | 48.9 | 194 | 170 | 3,896 |
| Time to detection, detected mutants (s) | qmon | 1,782 | 257 | 7.13 | 7.21 | 14.5 | 118 | 111 | 6,898 |
| Time to detection, detected mutants (s) | statistical | 1,928 | 346 | 7.09 | 21.3 | 70.9 | 305 | 284 | 11,640 |
| Time to detection, detected mutants (s) | proq | 2,031 | 321 | 7.09 | 28.3 | 63.8 | 234 | 206 | 11,567 |
| Time to detection, detected mutants (s) | liu | 2,036 | 320 | 7.09 | 21.3 | 63.8 | 234 | 213 | 11,551 |
| Time to detection, detected mutants (s) | qmon early stop (UB) | 1,782 | 117 | 7.13 | 7.21 | 7.34 | 22.2 | 15 | 6,168 |
| Time spent on missed mutants (s) | qmon | 1,078 | 147 | 7.13 | 7.2 | 7.28 | 14.5 | 7.29 | 3,850 |
| Time spent on missed mutants (s) | statistical | 932 | 389 | 21.3 | 42.5 | 63.8 | 156 | 113 | 5,349 |
| Time spent on missed mutants (s) | proq | 829 | 401 | 21.3 | 42.5 | 56.7 | 85 | 42.5 | 5,344 |
| Time spent on missed mutants (s) | liu | 824 | 403 | 21.3 | 42.5 | 56.7 | 78.1 | 35.5 | 5,344 |

Detected + missed = 2,860 for every method (QMON 1,782 + 1,078; statistical 1,928 + 932; Proq 2,031 + 829; Liu 2,036 + 824). QMON's counts match the paper.

---

## 2. Full-check time ratio per circuit (QMON ÷ baseline; below 1 = QMON faster)

| O_job (s) | Baseline | Median ratio | 95% CI (family bootstrap, 2,000 resamples) | Mean ratio | P25 | P75 | IQR | Circuits where QMON is faster |
|---|---|---|---|---|---|---|---|---|
| 0 | statistical | 0.151 | [0.125, 0.175] | 0.206 | 0.1 | 0.256 | 0.155 | 237 / 238 |
| 0 | proq | 0.151 | [0.125, 0.175] | 0.206 | 0.1 | 0.256 | 0.155 | 237 / 238 |
| 0 | liu | 0.151 | [0.125, 0.175] | 0.206 | 0.1 | 0.256 | 0.155 | 237 / 238 |
| 2 | statistical | 0.146 | [0.117, 0.169] | 0.194 | 0.0949 | 0.253 | 0.158 | 237 / 238 |
| 2 | proq | 0.146 | [0.118, 0.169] | 0.194 | 0.0949 | 0.253 | 0.158 | 237 / 238 |
| 2 | liu | 0.146 | [0.118, 0.169] | 0.194 | 0.0949 | 0.253 | 0.158 | 237 / 238 |
| 5 | statistical | 0.143 | [0.115, 0.166] | 0.188 | 0.0926 | 0.251 | 0.159 | 237 / 238 |
| 5 | proq | 0.143 | [0.115, 0.166] | 0.188 | 0.0926 | 0.252 | 0.159 | 237 / 238 |
| 5 | liu | 0.143 | [0.115, 0.166] | 0.188 | 0.0926 | 0.251 | 0.159 | 237 / 238 |

Run counts for comparison (from the stored plans): median B/K = 0.139; pooled ΣB / ΣK = 7,143 / 21,928 = 0.33. Largest B/K: grover-v-chain_indep_qiskit_9 (396 / 487 = 0.81), the likely circuit where QMON is not faster (to be confirmed).

---

## 3. Mutant recheck

QMON batches rebuilt on a random ~5% of mutants and re-timed (first seed only), to check that timing the original circuit is a fair approximation.

| Batches re-timed | Relative change in D, median | Relative change in D, max |
|---|---|---|
| 5,402 | 0.01% | 25.62% |

---

## 4. Resources before vs after transpiling to FakeKingston

One value per compiled circuit (median over seeds). n: original 238 circuits; QMON 7,143 batches; statistical 15,964 (one prefix per distinct checkpoint gate); Liu and Proq 21,928 each (one per checkpoint, ΣK).

### Metric definitions

| Metric | Definition |
|---|---|
| Qubits, before | Logical qubits as built (QMON: original + ancillas, at most 24) |
| Physical qubits, after | Device qubits the compiled circuit touches; can exceed logical because routing passes states through idle qubits |
| 2-qubit gates, before / (CZ) after | Entangling gates as built / native CZ gates after compiling |
| Routing SWAPs added | SWAPs inserted by routing (counted before translation; each becomes 3 CZ) |
| 1-qubit gates, before / after | After compiling these are rz / sx / x (rz takes 0 ns) |
| Operations, before / after | Gates + measures + resets (barriers and delays ignored) |
| Depth, before / after | Layers of operations, measure and reset included |
| Growth (after / before) | How much compiling inflates the circuit |
| … vs original, before / after | This circuit ÷ the original circuit (for QMON: instrumentation overhead) |
| Measures / Resets, after | Must equal before (check that nothing was dropped) |

### Original circuits (n = 238)

| Metric | Mean | Min | P25 | Median | P75 | IQR | Max |
|---|---|---|---|---|---|---|---|
| Qubits, before | 7.89 | 2 | 5 | 8 | 10 | 5 | 14 |
| Physical qubits, after | 7.94 | 2 | 5 | 8 | 11 | 6 | 15 |
| 2-qubit gates, before | 77.1 | 1 | 12 | 35.5 | 85 | 73 | 1,116 |
| 2-qubit gates (CZ), after | 212 | 1 | 21 | 77.5 | 263 | 242 | 2,826 |
| Routing SWAPs added | 44.1 | 0 | 3 | 14.5 | 52 | 49 | 461 |
| 1-qubit gates, before | 61.9 | 2 | 12 | 23 | 48 | 36 | 986 |
| 1-qubit gates, after | 713 | 6 | 87 | 287 | 844 | 757 | 10,308 |
| Operations, before | 146 | 5 | 31 | 63.5 | 153 | 122 | 1,628 |
| Operations, after | 933 | 9 | 115 | 372 | 1,118 | 1,003 | 13,161 |
| Depth, before | 73.3 | 4 | 13 | 26 | 55 | 42 | 1,124 |
| Depth, after | 427 | 7 | 57 | 224 | 510 | 453 | 7,318 |
| 2-qubit growth (after / before) | 2.47 | 0.857 | 1.75 | 2.47 | 3.12 | 1.37 | 4.67 |
| Depth growth (after / before) | 6.84 | 1.29 | 3.35 | 4.89 | 10.1 | 6.76 | 21.1 |
| Measures, after | 7.53 | 1 | 4 | 7 | 10 | 6 | 20 |
| Resets, after | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### QMON batches (n = 7,143)

| Metric | Mean | Min | P25 | Median | P75 | IQR | Max |
|---|---|---|---|---|---|---|---|
| Qubits, before | 21.5 | 3 | 20 | 22 | 24 | 4 | 24 |
| Physical qubits, after | 22.7 | 3 | 21 | 23 | 25 | 4 | 36 |
| 2-qubit gates, before | 499 | 2 | 138 | 414 | 601 | 463 | 3,220 |
| 2-qubit gates (CZ), after | 1,311 | 1 | 403 | 1,115 | 1,620 | 1,217 | 9,355 |
| Routing SWAPs added | 277 | 0 | 91 | 253 | 366 | 275 | 1,712 |
| 1-qubit gates, before | 501 | 4 | 140 | 440 | 753 | 613 | 2,047 |
| 1-qubit gates, after | 4,526 | 14 | 1,311 | 3,773 | 5,451 | 4,140 | 33,160 |
| Operations, before | 1,015 | 12 | 299 | 981 | 1,481 | 1,182 | 3,469 |
| Operations, after | 5,852 | 25 | 1,735 | 4,894 | 7,080 | 5,345 | 42,532 |
| Depth, before | 625 | 8 | 171 | 385 | 890 | 719 | 3,234 |
| Depth, after | 2,917 | 14 | 729 | 2,107 | 3,475 | 2,746 | 22,231 |
| 2-qubit growth (after / before) | 2.75 | 0.5 | 2.4 | 2.74 | 2.93 | 0.534 | 5.15 |
| Depth growth (after / before) | 5.45 | 1.16 | 3.72 | 4.42 | 5.88 | 2.16 | 20.4 |
| 2-qubit gates vs original, before | 1.71 | 1 | 1.29 | 1.55 | 1.89 | 0.597 | 8.22 |
| 2-qubit gates vs original, after | 1.92 | 0.995 | 1.38 | 1.7 | 2.08 | 0.699 | 22.8 |
| Depth vs original, before | 1.67 | 1 | 1.25 | 1.52 | 1.87 | 0.613 | 8.68 |
| Depth vs original, after | 1.73 | 0.827 | 1.29 | 1.55 | 1.93 | 0.633 | 12 |
| Measures, after | 12.8 | 2 | 11 | 13 | 14 | 3 | 42 |
| Resets, after | 2.7 | 1 | 1 | 2 | 3 | 2 | 28 |

### Statistical assertion checkpoint circuits (n = 15,964)

| Metric | n | Mean | Min | P25 | Median | P75 | IQR | Max |
|---|---|---|---|---|---|---|---|---|
| Qubits, before | 15,964 | 9.7 | 2 | 8 | 10 | 12 | 4 | 14 |
| Physical qubits, after | 15,964 | 9.81 | 2 | 8 | 10 | 12 | 4 | 17 |
| 2-qubit gates, before | 15,964 | 103 | 0 | 15 | 50 | 127 | 112 | 1,055 |
| 2-qubit gates (CZ), after | 15,964 | 239 | 0 | 26 | 104 | 298 | 272 | 2,681 |
| Routing SWAPs added | 15,964 | 46.1 | 0 | 3 | 19 | 61 | 58 | 443 |
| 1-qubit gates, before | 15,964 | 104 | 0 | 12 | 48 | 139 | 127 | 690 |
| 1-qubit gates, after | 15,964 | 842 | 0 | 95 | 361 | 1,033 | 938 | 9,760 |
| Operations, before | 15,964 | 217 | 3 | 39 | 111 | 291 | 252 | 1,204 |
| Operations, after | 15,964 | 1,091 | 4 | 130 | 474 | 1,338 | 1,208 | 12,448 |
| Depth, before | 15,964 | 134 | 2 | 17 | 60 | 146 | 129 | 1,062 |
| Depth, after | 15,964 | 579 | 1 | 69 | 249 | 633 | 564 | 6,938 |
| 2-qubit growth (after / before) | 15,066 | 2.12 | 0.5 | 1.54 | 2.15 | 2.56 | 1.03 | 4.71 |
| Depth growth (after / before) | 15,964 | 4.39 | 0.333 | 2.7 | 3.59 | 5.23 | 2.53 | 21.7 |
| 2-qubit gates vs original, before | 15,964 | 0.405 | 0 | 0.139 | 0.357 | 0.654 | 0.516 | 1 |
| 2-qubit gates vs original, after | 15,964 | 0.381 | 0 | 0.11 | 0.322 | 0.624 | 0.514 | 1.17 |
| Depth vs original, before | 15,964 | 0.438 | 0.00178 | 0.182 | 0.395 | 0.681 | 0.499 | 1 |
| Depth vs original, after | 15,964 | 0.398 | 0.000547 | 0.132 | 0.341 | 0.633 | 0.5 | 1.22 |
| Measures, after | 15,964 | 9.7 | 2 | 8 | 10 | 12 | 4 | 14 |
| Resets, after | 15,964 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### Liu (dynamic ancilla) checkpoint circuits (n = 21,928)

| Metric | Mean | Min | P25 | Median | P75 | IQR | Max |
|---|---|---|---|---|---|---|---|
| Qubits, before | 10.8 | 3 | 9 | 11 | 13 | 4 | 15 |
| Physical qubits, after | 9.96 | 2 | 7 | 10 | 13 | 6 | 20 |
| 2-qubit gates, before | 95.7 | 1 | 16 | 47 | 113 | 97 | 1,056 |
| 2-qubit gates (CZ), after | 222 | 1 | 30 | 105 | 272 | 242 | 2,707 |
| Routing SWAPs added | 43.9 | 0 | 4 | 20 | 56 | 52 | 447 |
| 1-qubit gates, before | 102 | 0 | 13 | 45 | 130 | 117 | 690 |
| 1-qubit gates, after | 779 | 5 | 110 | 361 | 925 | 815 | 9,844 |
| Operations, before | 198 | 3 | 32 | 95 | 257 | 225 | 1,198 |
| Operations, after | 1,003 | 7 | 140 | 467 | 1,196 | 1,056 | 12,552 |
| Depth, before | 126 | 3 | 17 | 55 | 133 | 116 | 1,063 |
| Depth, after | 530 | 6 | 77 | 246 | 564 | 487 | 6,960 |
| 2-qubit growth (after / before) | 2.14 | 0.667 | 1.51 | 2.16 | 2.59 | 1.09 | 4.79 |
| Depth growth (after / before) | 4.6 | 1 | 2.78 | 3.64 | 5.34 | 2.56 | 21.9 |
| 2-qubit gates vs original, before | 0.429 | 0.000896 | 0.157 | 0.376 | 0.677 | 0.52 | 2 |
| 2-qubit gates vs original, after | 0.411 | 0.000354 | 0.13 | 0.346 | 0.664 | 0.535 | 2.33 |
| Depth vs original, before | 0.459 | 0.00267 | 0.2 | 0.419 | 0.701 | 0.501 | 1.29 |
| Depth vs original, after | 0.418 | 0.00082 | 0.148 | 0.356 | 0.659 | 0.511 | 1.94 |
| Measures, after | 1 | 1 | 1 | 1 | 1 | 0 | 1 |
| Resets, after | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### Proq (projection) checkpoint circuits (n = 21,928)

The "before" circuit is the u/cx-expanded prefix used by `run_proq`, so its counts start higher than the other baselines.

| Metric | n | Mean | Min | P25 | Median | P75 | IQR | Max |
|---|---|---|---|---|---|---|---|---|
| Qubits, before | 21,928 | 9.83 | 2 | 8 | 10 | 12 | 4 | 14 |
| Physical qubits, after | 21,928 | 8.73 | 1 | 6 | 9 | 12 | 6 | 17 |
| 2-qubit gates, before | 21,928 | 116 | 0 | 19 | 56 | 133 | 114 | 1,588 |
| 2-qubit gates (CZ), after | 21,928 | 218 | 0 | 28 | 99 | 265 | 237 | 2,681 |
| Routing SWAPs added | 21,928 | 42.4 | 0 | 4 | 18 | 53 | 49 | 443 |
| 1-qubit gates, before | 21,928 | 169 | 2 | 28 | 81 | 210 | 182 | 1,672 |
| 1-qubit gates, after | 21,928 | 823 | 1 | 112 | 373 | 975 | 863 | 10,393 |
| Operations, before | 21,928 | 286 | 4 | 47 | 138 | 344 | 297 | 3,261 |
| Operations, after | 21,928 | 1,042 | 2 | 141 | 475 | 1,240 | 1,099 | 13,071 |
| Depth, before | 21,928 | 184 | 4 | 28 | 76 | 172 | 144 | 2,649 |
| Depth, after | 21,928 | 539 | 2 | 74 | 244 | 567 | 493 | 7,102 |
| 2-qubit growth (after / before) | 21,030 | 1.74 | 0.5 | 1.37 | 1.7 | 2.06 | 0.695 | 3.65 |
| Depth growth (after / before) | 21,928 | 2.9 | 0.5 | 2.31 | 2.76 | 3.51 | 1.2 | 14.2 |
| 2-qubit gates vs original, before | 21,928 | 0.521 | 0 | 0.173 | 0.429 | 0.782 | 0.609 | 2.33 |
| 2-qubit gates vs original, after | 21,928 | 0.391 | 0 | 0.117 | 0.329 | 0.634 | 0.517 | 1.62 |
| Depth vs original, before | 21,928 | 0.766 | 0.00356 | 0.258 | 0.562 | 0.95 | 0.692 | 3.82 |
| Depth vs original, after | 21,928 | 0.419 | 0.00041 | 0.143 | 0.353 | 0.661 | 0.517 | 1.71 |
| Measures, after | 21,928 | 1 | 1 | 1 | 1 | 1 | 0 | 1 |
| Resets, after | 21,928 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### Side-by-side summary (medians)

| | Original | QMON batch | Statistical | Liu | Proq |
|---|---|---|---|---|---|
| Qubits before → physical after | 8 → 8 | 22 → 23 | 10 → 10 | 11 → 10 | 10 → 9 |
| 2-qubit gates before → after | 35.5 → 77.5 | 414 → 1,115 | 50 → 104 | 47 → 105 | 56 → 99 |
| Routing SWAPs added | 14.5 | 253 | 19 | 20 | 18 |
| 2-qubit growth (after / before) | 2.47 | 2.74 | 2.15 | 2.16 | 1.70 |
| Depth growth (after / before) | 4.89 | 4.42 | 3.59 | 3.64 | 2.76 |

---

## 5. Checks

| Check | Result |
|---|---|
| Stored plan, K, K_qmon and B agree with the stored RQ3 results | Pass (all 238) |
| Measures or resets removed by compilation | 0 circuits |
| QMON detections / misses match the paper | 1,782 / 1,078 |
| QMON "before" counts match `resources_per_batch.csv` | Pending rerun. The first check compared batches by index (1,181 / 7,143 matched). Your RQ2 resources run and the stored RQ3 plan list the same batches in a different order for 90 circuits and group them differently for 2 (cdkm_ripple_carry_adder_8, full_adder_8). The check now matches batches by content. |
| Mutant recheck (D change from building on the mutant) | Median 0.01%, max 25.62% over 5,402 batches. Effect on run time still to quantify. |

## 6. Key findings

1. **Full check:** QMON median 2.4 s vs about 44 s for each baseline (O_job = 0); median time ratio 0.151 [0.125, 0.175]; QMON faster on 237 of 238 circuits.
2. **The wait between shots dominates.** 250 µs per shot outweighs every circuit's duration, so all three baselines cost about the same and QMON's speedup tracks its run-count advantage (median B/K = 0.139).
3. **Large circuits erode the advantage.** Pooled, QMON needs 33% of the baselines' runs but about 43% of their time, because its big batches take longer per shot.
4. **Time to detection:** QMON median 4.49 s vs 18.8–20.9 s. Means are close (93 s vs 97–105 s) because the paper's QMON runs every batch. Early stopping cuts QMON's mean to 42.5 s or less.
5. **Per-job overhead matters most for the baselines.** At O_job = 2 s their median full check doubles (43.9 → 85.9 s) unless runs are packed into one job; QMON barely changes.
6. **Compiling inflates QMON batches more than the original circuits.** 2-qubit growth ×2.74 vs ×2.47; 253 routing SWAPs per batch. QMON's 2-qubit overhead vs the original rises from 1.55× before to 1.70× after compiling (mean 1.71 → 1.92). Depth overhead barely changes (1.52× → 1.55×).

## Threats to validity

- No noise: detection outcomes come from the noise-free stored run.
- One calibration snapshot (2026-04-15); real devices drift.
- `estimate_duration` leaves out queue time, classical latency after mid-circuit measurements, and error mitigation.
- O_job is approximate. IBM splits large jobs into sub-jobs that each pay it, so "one job" is a best case for the baselines.
- Timing is per circuit and applied to all of its mutants (justified by the mutant recheck).