# RQ3 device-time estimates for FakeKingston backend

## Device-time estimates (8,192 shots per run)

| O_job (s) | Metric                                  | Method               |     n | Mean |  Min |  P25 | Median |  P75 |  IQR |    Max |
| --------: | --------------------------------------- | -------------------- | ----: | ---: | ---: | ---: | -----: | ---: | ---: | -----: |
|       0.0 | Full-check time per circuit (s)         | qmon                 |   238 | 88.9 | 2.13 | 2.21 |    2.4 | 33.7 | 31.5 |  2,633 |
|       0.0 | Full-check time per circuit (s)         | statistical          |   238 |  205 | 6.26 | 18.8 |   43.9 |  189 |  170 |  3,888 |
|       0.0 | Full-check time per circuit (s)         | proq                 |   238 |  206 | 6.26 | 18.8 |   43.9 |  189 |  170 |  3,909 |
|       0.0 | Full-check time per circuit (s)         | liu                  |   238 |  205 | 6.26 | 18.8 |   43.9 |  189 |  170 |  3,891 |
|       0.0 | Full-check time, one job (s)            | qmon                 |   238 | 88.9 | 2.13 | 2.21 |    2.4 | 33.7 | 31.5 |  2,633 |
|       0.0 | Full-check time, one job (s)            | statistical          |   238 |  205 | 6.26 | 18.8 |   43.9 |  189 |  170 |  3,888 |
|       0.0 | Full-check time, one job (s)            | proq                 |   238 |  206 | 6.26 | 18.8 |   43.9 |  189 |  170 |  3,909 |
|       0.0 | Full-check time, one job (s)            | liu                  |   238 |  205 | 6.26 | 18.8 |   43.9 |  189 |  170 |  3,891 |
|       0.0 | Time to detection, detected mutants (s) | qmon                 | 1,782 | 93.2 | 2.13 | 2.21 |   4.49 | 40.1 | 37.9 |  2,633 |
|       0.0 | Time to detection, detected mutants (s) | statistical          | 1,928 |  105 | 2.09 | 6.26 |   20.9 |   90 | 83.7 |  3,755 |
|       0.0 | Time to detection, detected mutants (s) | proq                 | 2,031 | 96.8 | 2.09 | 8.34 |   18.8 |   69 | 60.6 |  3,742 |
|       0.0 | Time to detection, detected mutants (s) | liu                  | 2,036 | 96.5 | 2.09 | 6.26 |   18.8 |   69 | 62.8 |  3,726 |
|       0.0 | Time to detection, detected mutants (s) | qmon early stop (UB) | 1,782 | 42.5 | 2.13 | 2.21 |   2.34 | 7.23 | 5.02 |  2,363 |
|       0.0 | Time spent on missed mutants (s)        | qmon                 | 1,078 | 62.6 | 2.13 |  2.2 |   2.28 | 4.49 | 2.29 |  1,870 |
|       0.0 | Time spent on missed mutants (s)        | statistical          |   932 |  124 | 6.26 | 12.5 |   18.8 | 45.9 | 33.3 |  1,639 |
|       0.0 | Time spent on missed mutants (s)        | proq                 |   829 |  129 | 6.26 | 12.5 |   16.7 |   25 | 12.5 |  1,634 |
|       0.0 | Time spent on missed mutants (s)        | liu                  |   824 |  129 | 6.26 | 12.5 |   16.7 | 23.1 | 10.5 |  1,634 |
|       2.0 | Full-check time per circuit (s)         | qmon                 |   238 |  149 | 4.13 | 4.21 |    4.4 | 61.7 | 57.4 |  4,339 |
|       2.0 | Full-check time per circuit (s)         | statistical          |   238 |  390 | 12.3 | 36.8 |   85.9 |  367 |  330 |  7,140 |
|       2.0 | Full-check time per circuit (s)         | proq                 |   238 |  390 | 12.3 | 36.8 |   85.9 |  367 |  330 |  7,161 |
|       2.0 | Full-check time per circuit (s)         | liu                  |   238 |  390 | 12.3 | 36.8 |   85.9 |  367 |  330 |  7,143 |
|       2.0 | Full-check time, one job (s)            | qmon                 |   238 | 90.9 | 4.13 | 4.21 |    4.4 | 35.7 | 31.5 |  2,635 |
|       2.0 | Full-check time, one job (s)            | statistical          |   238 |  207 | 8.26 | 20.8 |   45.9 |  191 |  170 |  3,890 |
|       2.0 | Full-check time, one job (s)            | proq                 |   238 |  208 | 8.26 | 20.8 |   45.9 |  191 |  170 |  3,911 |
|       2.0 | Full-check time, one job (s)            | liu                  |   238 |  207 | 8.26 | 20.8 |   45.9 |  191 |  170 |  3,893 |
|       2.0 | Time to detection, detected mutants (s) | qmon                 | 1,782 |  159 | 4.13 | 4.21 |   8.49 |   70 | 65.8 |  4,339 |
|       2.0 | Time to detection, detected mutants (s) | statistical          | 1,928 |  201 | 4.09 | 12.3 |   40.9 |  176 |  164 |  6,909 |
|       2.0 | Time to detection, detected mutants (s) | proq                 | 2,031 |  186 | 4.09 | 16.3 |   36.8 |  135 |  119 |  6,872 |
|       2.0 | Time to detection, detected mutants (s) | liu                  | 2,036 |  186 | 4.09 | 12.3 |   36.8 |  135 |  123 |  6,856 |
|       2.0 | Time to detection, detected mutants (s) | qmon early stop (UB) | 1,782 | 72.3 | 4.13 | 4.21 |   4.34 | 13.2 | 9.02 |  3,885 |
|       2.0 | Time spent on missed mutants (s)        | qmon                 | 1,078 | 96.2 | 4.13 |  4.2 |   4.28 | 8.49 | 4.29 |  2,662 |
|       2.0 | Time spent on missed mutants (s)        | statistical          |   932 |  230 | 12.3 | 24.5 |   36.8 | 89.9 | 65.3 |  3,123 |
|       2.0 | Time spent on missed mutants (s)        | proq                 |   829 |  238 | 12.3 | 24.5 |   32.7 |   49 | 24.5 |  3,118 |
|       2.0 | Time spent on missed mutants (s)        | liu                  |   824 |  239 | 12.3 | 24.5 |   32.7 | 45.1 | 20.5 |  3,118 |
|       5.0 | Full-check time per circuit (s)         | qmon                 |   238 |  239 | 7.13 | 7.21 |    7.4 |  104 | 96.4 |  6,898 |
|       5.0 | Full-check time per circuit (s)         | statistical          |   238 |  666 | 21.3 | 63.8 |    149 |  634 |  570 | 12,018 |
|       5.0 | Full-check time per circuit (s)         | proq                 |   238 |  666 | 21.3 | 63.8 |    149 |  634 |  570 | 12,039 |
|       5.0 | Full-check time per circuit (s)         | liu                  |   238 |  666 | 21.3 | 63.8 |    149 |  634 |  570 | 12,021 |
|       5.0 | Full-check time, one job (s)            | qmon                 |   238 | 93.9 | 7.13 | 7.21 |    7.4 | 38.7 | 31.5 |  2,638 |
|       5.0 | Full-check time, one job (s)            | statistical          |   238 |  210 | 11.3 | 23.8 |   48.9 |  194 |  170 |  3,893 |
|       5.0 | Full-check time, one job (s)            | proq                 |   238 |  211 | 11.3 | 23.8 |   48.9 |  194 |  170 |  3,914 |
|       5.0 | Full-check time, one job (s)            | liu                  |   238 |  210 | 11.3 | 23.8 |   48.9 |  194 |  170 |  3,896 |
|       5.0 | Time to detection, detected mutants (s) | qmon                 | 1,782 |  257 | 7.13 | 7.21 |   14.5 |  118 |  111 |  6,898 |
|       5.0 | Time to detection, detected mutants (s) | statistical          | 1,928 |  346 | 7.09 | 21.3 |   70.9 |  305 |  284 | 11,640 |
|       5.0 | Time to detection, detected mutants (s) | proq                 | 2,031 |  321 | 7.09 | 28.3 |   63.8 |  234 |  206 | 11,567 |
|       5.0 | Time to detection, detected mutants (s) | liu                  | 2,036 |  320 | 7.09 | 21.3 |   63.8 |  234 |  213 | 11,551 |
|       5.0 | Time to detection, detected mutants (s) | qmon early stop (UB) | 1,782 |  117 | 7.13 | 7.21 |   7.34 | 22.2 |   15 |  6,168 |
|       5.0 | Time spent on missed mutants (s)        | qmon                 | 1,078 |  147 | 7.13 |  7.2 |   7.28 | 14.5 | 7.29 |  3,850 |
|       5.0 | Time spent on missed mutants (s)        | statistical          |   932 |  389 | 21.3 | 42.5 |   63.8 |  156 |  113 |  5,349 |
|       5.0 | Time spent on missed mutants (s)        | proq                 |   829 |  401 | 21.3 | 42.5 |   56.7 |   85 | 42.5 |  5,344 |
|       5.0 | Time spent on missed mutants (s)        | liu                  |   824 |  403 | 21.3 | 42.5 |   56.7 | 78.1 | 35.5 |  5,344 |

## Full-check time ratio per circuit (below 1 = QMON faster)

| O_job (s) | QMON / baseline | Median ratio | 95% CI (family bootstrap) | Mean ratio |    P25 |   P75 |   IQR | Circuits where QMON is faster |
| --------: | --------------- | -----------: | ------------------------- | ---------: | -----: | ----: | ----: | ----------------------------- |
|       0.0 | statistical     |        0.151 | [0.125, 0.175]            |      0.206 |    0.1 | 0.256 | 0.155 | 237 / 238                     |
|       0.0 | proq            |        0.151 | [0.125, 0.175]            |      0.206 |    0.1 | 0.256 | 0.155 | 237 / 238                     |
|       0.0 | liu             |        0.151 | [0.125, 0.175]            |      0.206 |    0.1 | 0.256 | 0.155 | 237 / 238                     |
|       2.0 | statistical     |        0.146 | [0.117, 0.169]            |      0.194 | 0.0949 | 0.253 | 0.158 | 237 / 238                     |
|       2.0 | proq            |        0.146 | [0.118, 0.169]            |      0.194 | 0.0949 | 0.253 | 0.158 | 237 / 238                     |
|       2.0 | liu             |        0.146 | [0.118, 0.169]            |      0.194 | 0.0949 | 0.253 | 0.158 | 237 / 238                     |
|       5.0 | statistical     |        0.143 | [0.115, 0.166]            |      0.188 | 0.0926 | 0.251 | 0.159 | 237 / 238                     |
|       5.0 | proq            |        0.143 | [0.115, 0.166]            |      0.188 | 0.0926 | 0.252 | 0.159 | 237 / 238                     |
|       5.0 | liu             |        0.143 | [0.115, 0.166]            |      0.188 | 0.0926 | 0.251 | 0.159 | 237 / 238                     |

_Mutant recheck: 5402 batches, relative change in D: median 0.01%, max 25.62%._

## Resources before vs after transpiling to kingston

One value per compiled circuit; median over seeds.

| Circuit kind | Metric                            |      n |  Mean |      Min |   P25 | Median |   P75 |   IQR |    Max |
| ------------ | --------------------------------- | -----: | ----: | -------: | ----: | -----: | ----: | ----: | -----: |
| original     | Qubits, before                    |    238 |  7.89 |        2 |     5 |      8 |    10 |     5 |     14 |
| original     | Physical qubits, after            |    238 |  7.94 |        2 |     5 |      8 |    11 |     6 |     15 |
| original     | 2-qubit gates, before             |    238 |  77.1 |        1 |    12 |   35.5 |    85 |    73 |  1,116 |
| original     | 2-qubit gates (CZ), after         |    238 |   212 |        1 |    21 |   77.5 |   263 |   242 |  2,826 |
| original     | Routing SWAPs added               |    238 |  44.1 |        0 |     3 |   14.5 |    52 |    49 |    461 |
| original     | 1-qubit gates, before             |    238 |  61.9 |        2 |    12 |     23 |    48 |    36 |    986 |
| original     | 1-qubit gates, after              |    238 |   713 |        6 |    87 |    287 |   844 |   757 | 10,308 |
| original     | Operations, before                |    238 |   146 |        5 |    31 |   63.5 |   153 |   122 |  1,628 |
| original     | Operations, after                 |    238 |   933 |        9 |   115 |    372 | 1,118 | 1,003 | 13,161 |
| original     | Depth, before                     |    238 |  73.3 |        4 |    13 |     26 |    55 |    42 |  1,124 |
| original     | Depth, after                      |    238 |   427 |        7 |    57 |    224 |   510 |   453 |  7,318 |
| original     | 2-qubit growth (after / before)   |    238 |  2.47 |    0.857 |  1.75 |   2.47 |  3.12 |  1.37 |   4.67 |
| original     | Depth growth (after / before)     |    238 |  6.84 |     1.29 |  3.35 |   4.89 |  10.1 |  6.76 |   21.1 |
| original     | 2-qubit gates vs original, before |    238 |     1 |        1 |     1 |      1 |     1 |     0 |      1 |
| original     | 2-qubit gates vs original, after  |    238 |     1 |        1 |     1 |      1 |     1 |     0 |      1 |
| original     | Depth vs original, before         |    238 |     1 |        1 |     1 |      1 |     1 |     0 |      1 |
| original     | Depth vs original, after          |    238 |     1 |        1 |     1 |      1 |     1 |     0 |      1 |
| original     | Measures, after (check = before)  |    238 |  7.53 |        1 |     4 |      7 |    10 |     6 |     20 |
| original     | Resets, after (check = before)    |    238 |     0 |        0 |     0 |      0 |     0 |     0 |      0 |
| qmon         | Qubits, before                    |  7,143 |  21.5 |        3 |    20 |     22 |    24 |     4 |     24 |
| qmon         | Physical qubits, after            |  7,143 |  22.7 |        3 |    21 |     23 |    25 |     4 |     36 |
| qmon         | 2-qubit gates, before             |  7,143 |   499 |        2 |   138 |    414 |   601 |   463 |  3,220 |
| qmon         | 2-qubit gates (CZ), after         |  7,143 | 1,311 |        1 |   403 |  1,115 | 1,620 | 1,217 |  9,355 |
| qmon         | Routing SWAPs added               |  7,143 |   277 |        0 |    91 |    253 |   366 |   275 |  1,712 |
| qmon         | 1-qubit gates, before             |  7,143 |   501 |        4 |   140 |    440 |   753 |   613 |  2,047 |
| qmon         | 1-qubit gates, after              |  7,143 | 4,526 |       14 | 1,311 |  3,773 | 5,451 | 4,140 | 33,160 |
| qmon         | Operations, before                |  7,143 | 1,015 |       12 |   299 |    981 | 1,481 | 1,182 |  3,469 |
| qmon         | Operations, after                 |  7,143 | 5,852 |       25 | 1,735 |  4,894 | 7,080 | 5,345 | 42,532 |
| qmon         | Depth, before                     |  7,143 |   625 |        8 |   171 |    385 |   890 |   719 |  3,234 |
| qmon         | Depth, after                      |  7,143 | 2,917 |       14 |   729 |  2,107 | 3,475 | 2,746 | 22,231 |
| qmon         | 2-qubit growth (after / before)   |  7,143 |  2.75 |      0.5 |   2.4 |   2.74 |  2.93 | 0.534 |   5.15 |
| qmon         | Depth growth (after / before)     |  7,143 |  5.45 |     1.16 |  3.72 |   4.42 |  5.88 |  2.16 |   20.4 |
| qmon         | 2-qubit gates vs original, before |  7,143 |  1.71 |        1 |  1.29 |   1.55 |  1.89 | 0.597 |   8.22 |
| qmon         | 2-qubit gates vs original, after  |  7,143 |  1.92 |    0.995 |  1.38 |    1.7 |  2.08 | 0.699 |   22.8 |
| qmon         | Depth vs original, before         |  7,143 |  1.67 |        1 |  1.25 |   1.52 |  1.87 | 0.613 |   8.68 |
| qmon         | Depth vs original, after          |  7,143 |  1.73 |    0.827 |  1.29 |   1.55 |  1.93 | 0.633 |     12 |
| qmon         | Measures, after (check = before)  |  7,143 |  12.8 |        2 |    11 |     13 |    14 |     3 |     42 |
| qmon         | Resets, after (check = before)    |  7,143 |   2.7 |        1 |     1 |      2 |     3 |     2 |     28 |
| statistical  | Qubits, before                    | 15,964 |   9.7 |        2 |     8 |     10 |    12 |     4 |     14 |
| statistical  | Physical qubits, after            | 15,964 |  9.81 |        2 |     8 |     10 |    12 |     4 |     17 |
| statistical  | 2-qubit gates, before             | 15,964 |   103 |        0 |    15 |     50 |   127 |   112 |  1,055 |
| statistical  | 2-qubit gates (CZ), after         | 15,964 |   239 |        0 |    26 |    104 |   298 |   272 |  2,681 |
| statistical  | Routing SWAPs added               | 15,964 |  46.1 |        0 |     3 |     19 |    61 |    58 |    443 |
| statistical  | 1-qubit gates, before             | 15,964 |   104 |        0 |    12 |     48 |   139 |   127 |    690 |
| statistical  | 1-qubit gates, after              | 15,964 |   842 |        0 |    95 |    361 | 1,033 |   938 |  9,760 |
| statistical  | Operations, before                | 15,964 |   217 |        3 |    39 |    111 |   291 |   252 |  1,204 |
| statistical  | Operations, after                 | 15,964 | 1,091 |        4 |   130 |    474 | 1,338 | 1,208 | 12,448 |
| statistical  | Depth, before                     | 15,964 |   134 |        2 |    17 |     60 |   146 |   129 |  1,062 |
| statistical  | Depth, after                      | 15,964 |   579 |        1 |    69 |    249 |   633 |   564 |  6,938 |
| statistical  | 2-qubit growth (after / before)   | 15,066 |  2.12 |      0.5 |  1.54 |   2.15 |  2.56 |  1.03 |   4.71 |
| statistical  | Depth growth (after / before)     | 15,964 |  4.39 |    0.333 |   2.7 |   3.59 |  5.23 |  2.53 |   21.7 |
| statistical  | 2-qubit gates vs original, before | 15,964 | 0.405 |        0 | 0.139 |  0.357 | 0.654 | 0.516 |      1 |
| statistical  | 2-qubit gates vs original, after  | 15,964 | 0.381 |        0 |  0.11 |  0.322 | 0.624 | 0.514 |   1.17 |
| statistical  | Depth vs original, before         | 15,964 | 0.438 |  0.00178 | 0.182 |  0.395 | 0.681 | 0.499 |      1 |
| statistical  | Depth vs original, after          | 15,964 | 0.398 | 0.000547 | 0.132 |  0.341 | 0.633 |   0.5 |   1.22 |
| statistical  | Measures, after (check = before)  | 15,964 |   9.7 |        2 |     8 |     10 |    12 |     4 |     14 |
| statistical  | Resets, after (check = before)    | 15,964 |     0 |        0 |     0 |      0 |     0 |     0 |      0 |
| liu          | Qubits, before                    | 21,928 |  10.8 |        3 |     9 |     11 |    13 |     4 |     15 |
| liu          | Physical qubits, after            | 21,928 |  9.96 |        2 |     7 |     10 |    13 |     6 |     20 |
| liu          | 2-qubit gates, before             | 21,928 |  95.7 |        1 |    16 |     47 |   113 |    97 |  1,056 |
| liu          | 2-qubit gates (CZ), after         | 21,928 |   222 |        1 |    30 |    105 |   272 |   242 |  2,707 |
| liu          | Routing SWAPs added               | 21,928 |  43.9 |        0 |     4 |     20 |    56 |    52 |    447 |
| liu          | 1-qubit gates, before             | 21,928 |   102 |        0 |    13 |     45 |   130 |   117 |    690 |
| liu          | 1-qubit gates, after              | 21,928 |   779 |        5 |   110 |    361 |   925 |   815 |  9,844 |
| liu          | Operations, before                | 21,928 |   198 |        3 |    32 |     95 |   257 |   225 |  1,198 |
| liu          | Operations, after                 | 21,928 | 1,003 |        7 |   140 |    467 | 1,196 | 1,056 | 12,552 |
| liu          | Depth, before                     | 21,928 |   126 |        3 |    17 |     55 |   133 |   116 |  1,063 |
| liu          | Depth, after                      | 21,928 |   530 |        6 |    77 |    246 |   564 |   487 |  6,960 |
| liu          | 2-qubit growth (after / before)   | 21,928 |  2.14 |    0.667 |  1.51 |   2.16 |  2.59 |  1.09 |   4.79 |
| liu          | Depth growth (after / before)     | 21,928 |   4.6 |        1 |  2.78 |   3.64 |  5.34 |  2.56 |   21.9 |
| liu          | 2-qubit gates vs original, before | 21,928 | 0.429 | 0.000896 | 0.157 |  0.376 | 0.677 |  0.52 |      2 |
| liu          | 2-qubit gates vs original, after  | 21,928 | 0.411 | 0.000354 |  0.13 |  0.346 | 0.664 | 0.535 |   2.33 |
| liu          | Depth vs original, before         | 21,928 | 0.459 |  0.00267 |   0.2 |  0.419 | 0.701 | 0.501 |   1.29 |
| liu          | Depth vs original, after          | 21,928 | 0.418 |  0.00082 | 0.148 |  0.356 | 0.659 | 0.511 |   1.94 |
| liu          | Measures, after (check = before)  | 21,928 |     1 |        1 |     1 |      1 |     1 |     0 |      1 |
| liu          | Resets, after (check = before)    | 21,928 |     0 |        0 |     0 |      0 |     0 |     0 |      0 |
| proq         | Qubits, before                    | 21,928 |  9.83 |        2 |     8 |     10 |    12 |     4 |     14 |
| proq         | Physical qubits, after            | 21,928 |  8.73 |        1 |     6 |      9 |    12 |     6 |     17 |
| proq         | 2-qubit gates, before             | 21,928 |   116 |        0 |    19 |     56 |   133 |   114 |  1,588 |
| proq         | 2-qubit gates (CZ), after         | 21,928 |   218 |        0 |    28 |     99 |   265 |   237 |  2,681 |
| proq         | Routing SWAPs added               | 21,928 |  42.4 |        0 |     4 |     18 |    53 |    49 |    443 |
| proq         | 1-qubit gates, before             | 21,928 |   169 |        2 |    28 |     81 |   210 |   182 |  1,672 |
| proq         | 1-qubit gates, after              | 21,928 |   823 |        1 |   112 |    373 |   975 |   863 | 10,393 |
| proq         | Operations, before                | 21,928 |   286 |        4 |    47 |    138 |   344 |   297 |  3,261 |
| proq         | Operations, after                 | 21,928 | 1,042 |        2 |   141 |    475 | 1,240 | 1,099 | 13,071 |
| proq         | Depth, before                     | 21,928 |   184 |        4 |    28 |     76 |   172 |   144 |  2,649 |
| proq         | Depth, after                      | 21,928 |   539 |        2 |    74 |    244 |   567 |   493 |  7,102 |
| proq         | 2-qubit growth (after / before)   | 21,030 |  1.74 |      0.5 |  1.37 |    1.7 |  2.06 | 0.695 |   3.65 |
| proq         | Depth growth (after / before)     | 21,928 |   2.9 |      0.5 |  2.31 |   2.76 |  3.51 |   1.2 |   14.2 |
| proq         | 2-qubit gates vs original, before | 21,928 | 0.521 |        0 | 0.173 |  0.429 | 0.782 | 0.609 |   2.33 |
| proq         | 2-qubit gates vs original, after  | 21,928 | 0.391 |        0 | 0.117 |  0.329 | 0.634 | 0.517 |   1.62 |
| proq         | Depth vs original, before         | 21,928 | 0.766 |  0.00356 | 0.258 |  0.562 |  0.95 | 0.692 |   3.82 |
| proq         | Depth vs original, after          | 21,928 | 0.419 |  0.00041 | 0.143 |  0.353 | 0.661 | 0.517 |   1.71 |
| proq         | Measures, after (check = before)  | 21,928 |     1 |        1 |     1 |      1 |     1 |     0 |      1 |
| proq         | Resets, after (check = before)    | 21,928 |     0 |        0 |     0 |      0 |     0 |     0 |      0 |

## Checks

- Circuits where transpiling removed a measure or reset: **0**.
- QMON batches matching `resources_per_batch.csv` (qubits, ops, depth, 2q): **1181 / 7143**.
