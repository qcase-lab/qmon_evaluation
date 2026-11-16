"""Classical planning runtime of QMON, per circuit and per stage (RQ1/RQ2, Qmax = 24).

Run from the repo root (venv active), with NOTHING else heavy running
(other jobs slow the clock and spoil the timings):

    python evaluation/src/classical_planning_runtime.py

Times only QMON's CORE functions, as a real user would run them: none of the
authors' verification checks (crosscheck_selector, validate_partition_certificate,
_emit_batches / validate_artifact checks, ...) are inside the timed regions.

Stages, in the paper's order:
  1 selection     fast_analysis.analyze_per_gate_nolock                Algorithm 1
  2 final reads   coverage_rq2._last_source_gate_and_measured + filter  (tiny)
  3 cone tracing  circuits_selection.dfs_quantum_circuit + transformation   Algorithm 2
  4 grouping      utilities.filter_operation_list                       ancilla accounting
  5 FFD           batch_partition.first_fit_decreasing_partition        Algorithm 3, part 1
  6 partition     batch_partition.partition_nodes (FFD + ILP when triggered)
                  ILP time = partition time - FFD time, only when the ILP is triggered
                  (FFD gives > 1 batch and <= 120 groups fit the budget)
  7 construction  utilities.generate_monitoring_circuit, every batch circuit
  total = 1 + 2 + 3 + 4 + 6 + 7          (6 already contains the FFD)

Repeats: each stage runs up to 5 times on the same circuit and its MEDIAN is that
circuit's data point. Fewer runs when: the ILP is triggered (stage 6 runs once, it can
take up to 600 s), a stage's runs pass 60 s in total, or stage 7 (always once: one
circuit has 853 batches). The per-circuit CSV records how many runs each value used.

Note: with a Gurobi WLS license every ILP solve includes creating a Gurobi environment
(PuLP's manageEnv=True), so the ILP times include that start-up.

Writes to evaluation/results/:
  environment.txt              machine and package versions
  timing_per_circuit.csv       one row per circuit (resumes if the run stops)
  timing_rq2_summary.csv       mean, min, p25, median, p75, max over circuits (also printed)
  timing_ilp.csv               ILP triggered / hit the 600 s cap / saved a batch
"""

import contextlib                    # redirect_stdout: hide the authors' print() output
import csv                           # read/write the tables
import importlib.metadata            # package versions for environment.txt
import io                            # StringIO: where the hidden output goes
import math                          # ceil() for nearest-rank percentiles
import os                            # cpu count
import platform                      # OS / Python info
import statistics                    # median, mean
import sys                           # edit the import path
import time                          # perf_counter(): high-resolution wall clock
from pathlib import Path             # file paths

# Repo root = the nearest folder above this file that contains the authors' src/coverage_rq2.py.
REPO = next(p for p in Path(__file__).resolve().parents
            if (p / "src" / "coverage_rq2.py").exists())
sys.path.insert(0, str(REPO / "src"))               # so the authors' modules import

from qiskit import QuantumCircuit
from entanglement_disturbance import resolve_circuit_corpus, DEFAULT_MANIFEST, DEFAULT_QASM_DIR
from fast_analysis import analyze_per_gate_nolock, SKIP_OPS           # Algorithm 1
from circuits_selection import dfs_quantum_circuit, transformation    # Algorithm 2
from utilities import filter_operation_list, generate_monitoring_circuit
from batch_partition import (first_fit_decreasing_partition, partition_nodes,
                             DEFAULT_ILP_NODE_LIMIT)                  # 120 groups
from coverage_rq2 import QMAX, REFINEMENT_TIME_LIMIT_SECONDS, _last_source_gate_and_measured

TOL = 1e-12                          # separability tolerance (the paper's eps_sv)
REPEATS = 5                          # runs per stage; the median is kept
BUDGET_S = 60.0                      # stop repeating a stage once its runs pass this
RQ3_LIST = REPO / "inputs" / "rq3_circuits.txt"
OUT_DIR = Path(__file__).resolve().parents[1] / "results"   # evaluation/results/
PER_CIRCUIT_CSV = OUT_DIR / "timing_per_circuit.csv"

STAGES = [("t_selection_s", "Checkpoint selection (Algorithm 1)"),
          ("t_final_reads_s", "Final-read split"),
          ("t_cone_tracing_s", "Cone tracing (Algorithm 2)"),
          ("t_grouping_s", "Grouping / ancilla accounting"),
          ("t_ffd_s", "FFD packing"),
          ("t_ilp_s", "ILP refinement (circuits where it ran)"),
          ("t_construction_s", "Batch circuit construction"),
          ("t_planning_total_s", "Total planning time")]


# ============================================================================
# Helpers
# ============================================================================
def timed(fn, *args, repeats=REPEATS, budget_s=BUDGET_S, **kwargs):
    """Run fn up to `repeats` times. Returns (median seconds, runs done, last result)."""
    times = []
    result = None
    for _ in range(repeats):
        start = time.perf_counter()                 # clock before
        result = fn(*args, **kwargs)                # the work being timed
        times.append(time.perf_counter() - start)   # elapsed seconds
        if sum(times) >= budget_s:                  # long stage: enough samples
            break
    return statistics.median(times), len(times), result


def quiet(fn, *args, **kwargs):
    """Call fn and throw away what it prints (the authors' helpers print a lot)."""
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)


def machine_info():
    """Machine and package versions, for the paper's setup section."""
    lines = [f"OS: {platform.platform()}",
             f"Python: {platform.python_version()}",
             f"Logical CPUs: {os.cpu_count()}"]
    try:                                                     # Linux / WSL only
        cpu = next(l for l in Path("/proc/cpuinfo").read_text().splitlines()
                   if l.startswith("model name"))
        lines.append(f"CPU: {cpu.split(':', 1)[1].strip()}")
        mem = next(l for l in Path("/proc/meminfo").read_text().splitlines()
                   if l.startswith("MemTotal"))
        lines.append(f"RAM visible to WSL: {int(mem.split()[1]) / 1024 ** 2:.1f} GiB")
    except (OSError, StopIteration):
        pass
    for pkg in ["qiskit", "qiskit-aer", "numpy", "scipy", "pulp", "gurobipy"]:
        try:
            lines.append(f"{pkg}: {importlib.metadata.version(pkg)}")
        except importlib.metadata.PackageNotFoundError:
            lines.append(f"{pkg}: not installed")
    lines.append(f"Repeats per stage: {REPEATS} (median), budget {BUDGET_S:.0f} s; Qmax = {QMAX}")
    return "\n".join(lines) + "\n"


# ============================================================================
# One circuit
# ============================================================================
def time_circuit(key, qc, in_rq3):
    """Time every planning stage on one circuit. Returns one CSV row (a dict)."""
    row = {"circuit": key, "rq3": in_rq3, "num_qubits": qc.num_qubits,
           "gates": sum(inst.operation.name not in SKIP_OPS for inst in qc.data)}

    # ---- Stage 1: Algorithm 1 ---------------------------------------------------
    # Statevector simulation gate by gate; after each gate, a separability test on
    # each qubit it touched. paths[q] = gate indices where q is separable (candidates).
    t, n, (res, _, paths) = timed(analyze_per_gate_nolock, qc, tol=TOL)
    row["t_selection_s"], row["n_selection"] = t, n

    # ---- Stage 2: final-read split ----------------------------------------------
    # Candidates at a measured qubit's last gate are read by the final measurement.
    def split_final_reads():
        candidates = {(g, q) for q, gates in paths.items() for g in gates}
        last_gate, measured = _last_source_gate_and_measured(qc)
        final = {(g, q) for g, q in candidates if q in measured and g == last_gate[q]}
        return candidates - final                     # mid-circuit candidates
    t, n, mid = timed(split_final_reads)
    row["t_final_reads_s"], row["n_final_reads"] = t, n

    # ---- Stage 3: Algorithm 2 (cone tracing) -------------------------------------
    # For each mid-circuit candidate: backward causal cone -> list of gates to replay.
    by_point = {(r[0], r[2]): r for rows in res.values() for r in rows}   # name, p0, p1
    def trace_cones():
        operation_rows = []
        for gate, qubit in sorted(mid):
            cone = dfs_quantum_circuit(qc, qubit, gate, set(), [])
            replay = transformation(qc, qubit, cone, [])
            _, name, _, p0, p1 = by_point[(gate, qubit)]
            operation_rows.append([gate, name, qubit, p0, p1, replay])
        return {key: operation_rows} if operation_rows else {}
    t, n, operation_list = timed(trace_cones)
    row["t_cone_tracing_s"], row["n_cone_tracing"] = t, n

    # ---- Stage 4: grouping + ancilla accounting ------------------------------------
    # One group per gate index; ancillas = other qubits in the group's union cone.
    def group():
        constraint, members = {"num_oq": qc.num_qubits}, {}
        if operation_list:
            _, extra = filter_operation_list(key, operation_list, 10 ** 7)
            for gate in sorted({g for g, _ in mid}):
                members[gate] = sorted(q for g, q in mid if g == gate)
                constraint[gate] = {"num_eq": len(extra[gate]), "qubits": members[gate]}
        return constraint, members
    t, n, (constraint, members) = timed(quiet, group)
    row["t_grouping_s"], row["n_grouping"] = t, n

    # ---- Stage 5: FFD packing --------------------------------------------------------
    t_ffd, n, (ffd_batches, _, inventory) = timed(first_fit_decreasing_partition,
                                                  constraint, QMAX)
    row["t_ffd_s"], row["n_ffd"] = t_ffd, n

    # ---- Stage 6: partition (FFD + ILP) ----------------------------------------------
    # The ILP runs only if FFD made > 1 batch and <= 120 groups fit the budget.
    triggered = (len(ffd_batches) > 1
                 and inventory["feasible_item_count"] <= DEFAULT_ILP_NODE_LIMIT)
    t_part, n, (batches, _) = timed(
        partition_nodes, constraint, QMAX,
        refinement_time_limit_seconds=REFINEMENT_TIME_LIMIT_SECONDS,
        repeats=1 if triggered else REPEATS)          # an ILP solve can take 600 s
    t_ilp = max(t_part - t_ffd, 0.0) if triggered else None
    row["t_partition_s"], row["n_partition"] = t_part, n
    row["t_ilp_s"] = t_ilp if triggered else ""
    row["ilp_triggered"] = triggered
    row["ilp_hit_cap"] = (t_ilp >= REFINEMENT_TIME_LIMIT_SECONDS) if triggered else ""
    row["ilp_saved_batch"] = (len(batches) < len(ffd_batches)) if triggered else ""
    row["ffd_batches"], row["batches"] = len(ffd_batches), len(batches)

    # ---- Stage 7: batch circuit construction -----------------------------------------
    batches = sorted(({"nodes": sorted(b["nodes"])} for b in batches),
                     key=lambda b: tuple(b["nodes"]))          # the authors' batch order
    def construct():
        circuits = []
        for batch in batches:
            picked = sorted({q for g in batch["nodes"] for q in members[g]})
            answer = {"picked_nodes": batch["nodes"], "picked_qubits": picked,
                      "obj1": len(batch["nodes"]), "obj2": len(picked)}
            circuits.append(generate_monitoring_circuit(qc, key, operation_list,
                                                        10 ** 7, answer))
        return circuits
    t, n, _ = timed(quiet, construct, repeats=1)      # once: up to 853 circuits
    row["t_construction_s"], row["n_construction"] = t, n

    # ---- Total ----------------------------------------------------------------------
    row["t_planning_total_s"] = (row["t_selection_s"] + row["t_final_reads_s"]
                                 + row["t_cone_tracing_s"] + row["t_grouping_s"]
                                 + row["t_partition_s"] + row["t_construction_s"])
    return row


# ============================================================================
# Tables
# ============================================================================
def describe(values):
    """mean, min, p25, median, p75, max (nearest-rank percentiles, as in the paper)."""
    v = sorted(values)
    n = len(v)
    rank = lambda p: v[max(math.ceil(p * n), 1) - 1]
    return [statistics.mean(v), v[0], rank(0.25), statistics.median(v), rank(0.75), v[-1]]


def fmt_s(x):
    """Seconds, readable across many orders of magnitude."""
    return f"{x:.2e}" if x < 0.01 else f"{x:,.3f}"


def print_table(title, header, rows):
    widths = [max(len(str(r[i])) for r in [header] + rows) for i in range(len(header))]
    line = lambda r: "  ".join(str(c).ljust(w) for c, w in zip(r, widths))
    print(f"\n{title}\n")
    print(line(header))
    print("  ".join("-" * w for w in widths))
    for r in rows:
        print(line(r))


def write_csv(path, header, rows):
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "environment.txt").write_text(machine_info())

    frame = resolve_circuit_corpus(DEFAULT_MANIFEST, DEFAULT_QASM_DIR)   # the 310 circuits
    qasm_dir = Path(frame["qasm_dir"])
    rq3 = {line.strip() + ".qasm" for line in RQ3_LIST.read_text().splitlines()
           if line.strip()}                                               # the 238 subset

    done = set()                                       # resume: skip finished circuits
    if PER_CIRCUIT_CSV.exists():
        with PER_CIRCUIT_CSV.open(newline="") as f:
            done = {r["circuit"] for r in csv.DictReader(f)}

    for i, entry in enumerate(frame["circuits"], start=1):
        key = entry["circuit"]
        if key in done:
            continue
        print(f"[{i}/{frame['circuit_count']}] {key}", flush=True)
        qc = QuantumCircuit.from_qasm_file(str(qasm_dir / key))
        row = time_circuit(key, qc, key in rq3)
        new_file = not PER_CIRCUIT_CSV.exists()
        with PER_CIRCUIT_CSV.open("a", newline="") as f:      # save after every circuit
            w = csv.DictWriter(f, fieldnames=list(row))
            if new_file:
                w.writeheader()
            w.writerow(row)

    # ---- Summary over circuits (read back, so resumed runs are included) ------------
    with PER_CIRCUIT_CSV.open(newline="") as f:
        rows = list(csv.DictReader(f))

    header = ["Scope", "Stage", "n", "Mean (s)", "Min (s)", "P25 (s)", "Median (s)",
              "P75 (s)", "Max (s)"]
    table = []
    for scope, keep in [("All 310", lambda r: True), ("RQ3 238", lambda r: r["rq3"] == "True")]:
        subset = [r for r in rows if keep(r)]
        for field, label in STAGES:
            values = [float(r[field]) for r in subset if r[field] != ""]   # ILP: where it ran
            stats = [fmt_s(s) for s in describe(values)] if values else [""] * 6
            table.append([scope, label, len(values)] + stats)
    print_table(f"Classical planning runtime per circuit, Qmax = {QMAX} "
                f"(median of up to {REPEATS} runs per stage)", header, table)
    write_csv(OUT_DIR / "timing_rq2_summary.csv", header, table)

    ilp_header = ["Scope", "Circuits", "ILP triggered", "Hit 600 s cap", "Saved a batch"]
    ilp_table = []
    for scope, keep in [("All 310", lambda r: True), ("RQ3 238", lambda r: r["rq3"] == "True")]:
        subset = [r for r in rows if keep(r)]
        ilp_table.append([scope, len(subset),
                          sum(r["ilp_triggered"] == "True" for r in subset),
                          sum(r["ilp_hit_cap"] == "True" for r in subset),
                          sum(r["ilp_saved_batch"] == "True" for r in subset)])
    print_table("ILP refinement", ilp_header, ilp_table)
    write_csv(OUT_DIR / "timing_ilp.csv", ilp_header, ilp_table)


if __name__ == "__main__":
    main()