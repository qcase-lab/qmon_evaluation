"""Show what the FakeKingston snapshot knows about ibm_kingston.

Run from the repo root, venv active:
    python evaluation/src/kingston_calibration.py

Prints: calibration date, device basics, every native instruction with its duration
(and error rate) across all qubits / qubit pairs, and the per-shot constants our
job-time formula uses.
"""

import warnings
from statistics import median
from qiskit_ibm_runtime.fake_provider import FakeProviderForBackendV2
from qiskit_ibm_runtime.fake_provider import FakeKingston

warnings.filterwarnings("ignore")

backend = FakeKingston()                                  # loads conf_kingston.json + props_kingston.json
target = backend.target                                   # the table the compiler and estimate_duration read
props = backend.properties()                              # the raw calibration snapshot

# ---- 1. Device basics ------------------------------------------------------------
print(f"Backend:            {backend.name}")
print(f"Calibration date:   {props.last_update_date}")    # when IBM measured these numbers
print(f"Qubits:             {backend.num_qubits}")
edges = {tuple(sorted(e)) for e in target.build_coupling_map().get_edges()}
print(f"Connected pairs:    {len(edges)}")                # pairs that can run a CZ directly
print(f"Time unit dt:       {backend.dt * 1e9:.3f} ns")   # control-electronics clock tick
rep = backend.configuration().default_rep_delay           # wait between shots, in seconds
print(f"Wait between shots: {rep * 1e6:.0f} us (default_rep_delay)")

# ---- 2. Native instructions and their durations -----------------------------------
# For each instruction the target stores one entry per qubit (1-qubit ops) or per
# connected pair (2-qubit ops): duration in seconds and error rate, copied from the
# calibration's gate_length / readout_length and gate_error / readout_error.
print("\nNative instruction set (durations across all qubits or pairs)\n")
print(f"{'instruction':<12}{'acts on':<9}{'entries':>8}"
      f"{'min ns':>9}{'median ns':>11}{'max ns':>9}{'median error':>14}")
for name in sorted(target.operation_names):
    entries = [p for p in target[name].values() if p is not None]   # skip ops with no data
    durs = [p.duration for p in entries if p.duration is not None]
    if not durs:                                          # delay, if_else, ...: no fixed duration
        print(f"{name:<12}{'-':<9}{'-':>8}   (no fixed duration: directive or control flow)")
        continue
    errs = [p.error for p in entries if p.error is not None]
    qargs = next(q for q, p in target[name].items() if p is not None)
    print(f"{name:<12}{f'{len(qargs)} qubit':<9}{len(durs):>8}"
          f"{min(durs) * 1e9:>9.0f}{median(durs) * 1e9:>11.0f}{max(durs) * 1e9:>9.0f}"
          f"{(f'{median(errs):.2e}' if errs else '-'):>14}")

# ---- 3. Coherence (not used for time; this is the noise side) ----------------------
t1 = [qp.t1 for qp in target.qubit_properties if qp and qp.t1]
t2 = [qp.t2 for qp in target.qubit_properties if qp and qp.t2]
print(f"\nT1 median: {median(t1) * 1e6:.0f} us    T2 median: {median(t2) * 1e6:.0f} us")

# ---- 4. What our job-time formula takes from this backend -------------------------
resets = [p.duration for p in target["reset"].values() if p and p.duration]
print("\nPer-shot constants used in T_run = O_job + 8192 x (t_rep + t_init + D):")
print(f"  t_rep  (wait between shots) = {rep * 1e6:.1f} us")
print(f"  t_init (median reset)       = {median(resets) * 1e6:.3f} us")
print("  D comes from estimate_duration on each compiled circuit.")