"""Resource metrics for QMON, BEFORE transpilation (RQ2 deployment plans, Qmax = 24).
Baselines: only their run count K per full scan is reported (one run per numerical
candidate, paper Table IV).
TODO: per-run resources of the baselines' checkpoint
circuits (qubits, gates, depth) for each baseline
also add totals (liek total qubits, total ancillas)
"""

import contextlib                    # redirect_stdout: hide the authors' print() output
import csv                           # write the output tables
import io                            # StringIO: where the hidden output goes
import math                          # ceil() for nearest-rank percentiles
import os                            # cpu count, atomic file replace
import pickle                        # per-circuit cache files
import statistics                    # mean, median
import sys                           # edit the import path
import traceback                     # full error text for failed circuits
from multiprocessing import Pool     # run circuits in parallel
from pathlib import Path             # file paths

# Repo root = the nearest folder above this file that contains the authors' src/coverage_rq2.py,
# so the script works wherever it is placed inside the repo.
REPO = next(p for p in Path(__file__).resolve().parents
            if (p / "src" / "coverage_rq2.py").exists())
sys.path.insert(0, str(REPO / "src"))               # so the authors' modules import

from qiskit import QuantumCircuit
import coverage_rq2 as rq2                                            # to restore _validate_record
from entanglement_disturbance import (resolve_circuit_corpus, DEFAULT_MANIFEST,
                                      DEFAULT_QASM_DIR, stable_hash)
from rq1_certificate_check import crosscheck_selector                 # Algorithm 1 (+ recheck)
from utilities import generate_monitoring_circuit                     # builds a batch circuit
from coverage_rq2 import (
    QMAX,                         # 24: qubit budget per instrumented run
    SCHEMA,                       # artifact schema name (as build_artifact writes it)
    protocol_descriptor,          # artifact protocol block (as build_artifact writes it)
    summarize,                    # artifact summary (as build_artifact writes it)
    evaluate_circuit,             # the authors' full pipeline for ONE circuit
    _validate_record,             # the authors' per-circuit validation
    validate_artifact,            # the authors' whole-run validation
    _build_operation_list,        # Algorithm 2 + final-read split (with checks)
    _group_demands,               # grouping + ancillas + packing (with checks)
    executable_operation_count,   # operations, barriers ignored
)

WORKERS = min(4, os.cpu_count() or 1)   # parallel processes (your laptop: 4 cores)
SHOTS = 8192                            # shots per run, as in the paper
RQ3_LIST = REPO / "inputs" / "rq3_circuits.txt"
OUT_DIR = Path(__file__).resolve().parents[1] / "results"   # evaluation/results/
CACHE_DIR = OUT_DIR / "resources_cache"                      # one file per finished circuit


def quiet(fn, *args, **kwargs):
    """Call fn and throw away what it prints (the authors' helpers print a lot)."""
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)


def two_qubit_gates(circuit):
    """Gates acting on exactly 2 qubits (a barrier can span 2 qubits; skip it).
    All 310 benchmark circuits use only 1- and 2-qubit gates."""
    return sum(1 for inst in circuit.data
               if inst.operation.num_qubits == 2 and inst.operation.name != "barrier")


# ============================================================================
# 2-qubit gates per batch (rebuilt from the authors' validated plan)
# ============================================================================
def batch_two_qubit_counts(qc, key, record):
    """2-qubit gate count of each batch circuit, in the authors' batch order."""
    # Same inputs evaluate_circuit used: Algorithm 1 rows -> operation list.
    check = crosscheck_selector(qc)
    operation_list, prebudget, _ = _build_operation_list(qc, key, check["selected_points"])
    # Hand _group_demands the STORED plan so nothing is re-solved.
    override = {"batches": record["batches"],                    # gate_groups + ancilla_cost
                "infeasible_gate_groups": record["infeasible_gate_groups"],
                "partition_provenance": record["partition_provenance"]}
    group_demands, batches, _, _ = _group_demands(qc, key, operation_list, prebudget,
                                                  partition_override=override)
    members = {g["gate"]: g["members"] for g in group_demands}   # gate -> monitored qubits
    counts = []
    for batch, stored in zip(batches, record["batches"]):
        assert list(batch["nodes"]) == list(stored["gate_groups"])     # same batch
        picked_qubits = sorted({q for g in batch["nodes"] for q in members[g]})
        answer = {"picked_nodes": list(batch["nodes"]), "picked_qubits": picked_qubits,
                  "obj1": len(batch["nodes"]), "obj2": len(picked_qubits)}   # as _emit_batches
        circuit = quiet(generate_monitoring_circuit, qc, key, operation_list, 10 ** 7, answer)
        # Rebuilt circuit must be the one the authors measured.
        assert executable_operation_count(circuit) == stored["emitted_executable_operation_count"]
        counts.append(two_qubit_gates(circuit))
    return counts


# ============================================================================
# One circuit, in a worker process
# ============================================================================
def cache_file(key):
    return CACHE_DIR / (key + ".pkl")


def load_cached(key):
    """The cached result of one circuit, or None if it is missing or failed."""
    path = cache_file(key)
    if not path.exists():
        return None
    with path.open("rb") as f:
        result = pickle.load(f)
    return None if "error" in result else result


def process_circuit(job):
    """Steps 1-3 for one circuit; saves the result to the cache. Runs in a worker."""
    entry, qasm_dir = job
    qasm_dir = Path(qasm_dir)
    key = entry["circuit"]
    try:
        status, record = evaluate_circuit(entry, qasm_dir)        # 1. authors' pipeline
        _validate_record(record, entry, qasm_dir)                 # 2. authors' validation
        qc = QuantumCircuit.from_qasm_file(str(qasm_dir / key))
        result = {"status": status, "record": record,             # 3. 2-qubit gates
                  "tq_counts": batch_two_qubit_counts(qc, key, record),
                  "tq_original": two_qubit_gates(qc)}
    except Exception as error:                                    # keep going; rerun retries it
        result = {"error": f"{type(error).__name__}: {error}",
                  "traceback": traceback.format_exc()}
    tmp = CACHE_DIR / (key + ".tmp")                              # write, then rename:
    with tmp.open("wb") as f:                                     # a half-written file
        pickle.dump(result, f)                                    # never looks finished
    os.replace(tmp, cache_file(key))
    return key, "error" in result


# ============================================================================
# Resource rows
# ============================================================================
def batch_resources(stored, tq_batch, tq_original):
    """Resources of ONE batch circuit. `stored` = the authors' stats for this batch."""
    return {
        "qubits": stored["emitted_total_qubits"],                 # original + ancillas (<= 24)
        "ancillas": stored["ancilla_cost"],
        "monitor_groups": stored["monitor_group_count"],
        "checkpoints": stored["monitor_point_count"],             # monitored qubits
        "mid_measurements": stored["monitor_measurement_count"],  # = checkpoints
        "resets": stored["monitor_reset_count"],                  # = checkpoints
        "replay_gates": stored["replay_gate_count"],
        "operations": stored["emitted_executable_operation_count"],
        # batch operations / original operations
        "ops_ratio": stored["emitted_executable_operation_count"]
                     / stored["source_executable_operation_count"],
        "depth": stored["emitted_executable_depth"],
        "depth_ratio": stored["depth_inflation_ratio"],           # batch depth / original depth
        "two_qubit_gates": tq_batch,
        "two_qubit_gates_added": tq_batch - tq_original,          # 2-qubit gates in the replay
        "two_qubit_ratio": tq_batch / tq_original if tq_original else None,
    }


def circuit_resources(record, batch_rows, in_rq3):
    """Resources of a FULL QMON scan of one circuit (all its batches)."""
    m = record["gate_count"]                                  # unitary gates of the original
    b = record["batch_count"]                                 # B = runs in a full scan
    g_replay = sum(r["replay_gates"] for r in batch_rows)     # G_replay
    e_deploy = record["emitted_mid_point_count"]              # E_deploy (mid-circuit)
    return {
        "circuit": record["circuit"],
        "rq3": in_rq3,                                        # in the 238-circuit subset
        "num_qubits": record["num_qubits"],
        "gates_m": m,
        "batches_B": b,
        "shots": b * SHOTS,                                   # B x 8,192
        "qmon_checkpoints_Kqmon": record["deployed_observable_point_count"],  # mid + final reads
        "mid_circuit_checkpoints": e_deploy,
        "final_reads": record["final_read_point_count"],
        "dropped_groups": record["infeasible_gate_group_count"],   # too big for Qmax = 24
        "baseline_runs_K": record["certificate_selected_point_count"],   # one run per candidate
        "max_qubits_per_batch": max((r["qubits"] for r in batch_rows),
                                    default=record["num_qubits"]),
        "max_ancillas_per_batch": max((r["ancillas"] for r in batch_rows), default=0),
        "replay_gates_total": g_replay,
        "two_qubit_gates_added_total": sum(r["two_qubit_gates_added"] for r in batch_rows),
        "depth_ratio_max": max((r["depth_ratio"] for r in batch_rows), default=1.0),
        "operations_full_scan": sum(r["operations"] for r in batch_rows),
        # Paper Eq. 9: planned counted-operation multiplier.
        #   mu_op = (B*m + G_replay + 2*E_deploy) / m
        # B*m: every batch reruns the whole original circuit; G_replay: replayed cone
        # gates; 2*E_deploy: one measure + one reset per checkpoint. Terminal
        # measurements, barriers and ancilla allocation are not counted.
        "mu_op": (b * m + g_replay + 2 * e_deploy) / m,
    }


# ============================================================================
# Tables
# ============================================================================
def describe(values):
    """mean, min, p25, median, p75, max (nearest-rank percentiles, as in the paper)."""
    v = sorted(values)
    n = len(v)
    rank = lambda p: v[max(math.ceil(p * n), 1) - 1]
    return [statistics.mean(v), v[0], rank(0.25), statistics.median(v), rank(0.75), v[-1]]


def fmt(x):
    """Integers with thousands separators; other numbers with 2 decimals."""
    return f"{x:,.0f}" if float(x).is_integer() else f"{x:,.2f}"


def print_table(title, header, rows):
    widths = [max(len(str(r[i])) for r in [header] + rows) for i in range(len(header))]
    line = lambda r: "  ".join(str(c).ljust(w) for c, w in zip(r, widths))
    print(f"\n{title}\n")
    print(line(header))
    print("  ".join("-" * w for w in widths))
    for r in rows:
        print(line(r))


def stat_rows(records, metrics, scope):
    """One row per metric: scope, label, n, mean, min, p25, median, p75, max."""
    rows = []
    for label, field in metrics:
        values = [r[field] for r in records if r[field] is not None]
        rows.append([scope, label, len(values)] + [fmt(s) for s in describe(values)])
    return rows


def write_csv(path, header, rows):
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main():
    frame = resolve_circuit_corpus(DEFAULT_MANIFEST, DEFAULT_QASM_DIR)   # the 310 circuits
    rq3 = {line.strip() + ".qasm" for line in RQ3_LIST.read_text().splitlines()
           if line.strip()}                                               # the 238 subset
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # ---- Steps 1-3 in parallel; finished circuits are skipped (resume) -------------
    todo = [e for e in frame["circuits"] if load_cached(e["circuit"]) is None]
    print(f"{len(frame['circuits']) - len(todo)} circuits already done, "
          f"{len(todo)} to go, {WORKERS} workers", flush=True)
    jobs = [(entry, frame["qasm_dir"]) for entry in todo]
    with Pool(WORKERS) as pool:
        for n, (key, failed) in enumerate(pool.imap_unordered(process_circuit, jobs), 1):
            print(f"[{n}/{len(todo)}] {key}{'  ERROR' if failed else ''}", flush=True)

    results = {e["circuit"]: load_cached(e["circuit"]) for e in frame["circuits"]}
    failed = [key for key, result in results.items() if result is None]
    if failed:
        for key in failed:
            with cache_file(key).open("rb") as f:
                print(f"\n{key}:\n{pickle.load(f)['traceback']}")
        raise SystemExit(f"{len(failed)} circuits failed; fix and rerun (finished ones are kept)")

    # ---- Step 4: assemble the artifact exactly as build_artifact does, validate it ---
    records = sorted((r["record"] for r in results.values()),
                     key=lambda record: record["attempt_index"])
    artifact = {
        "schema": SCHEMA,
        "protocol": protocol_descriptor(),
        "corpus": {"manifest_sha256": frame["manifest_sha256"],
                   "corpus_sha256": frame["corpus_sha256"],
                   "circuit_count": frame["circuit_count"]},
        "circuit_status": {key: r["status"] for key, r in results.items()},
        "record_count": len(records),
        "records_sha256": stable_hash(records),
        "summary": summarize(records),
        "records": records,
    }
    # validate_artifact calls _validate_record on every circuit; the workers already did,
    # so it is switched off here and switched back on right after.
    rq2._validate_record = lambda *args, **kwargs: None
    try:
        validate_artifact(artifact, frame, require_complete=True)
    finally:
        rq2._validate_record = _validate_record
    print("authors' whole-run validation passed", flush=True)

    # ---- Resource rows ------------------------------------------------------------
    per_batch, per_circuit = [], []
    for record in records:
        key = record["circuit"]
        r = results[key]
        rows = [batch_resources(stored, tq, r["tq_original"])
                for stored, tq in zip(record["batches"], r["tq_counts"])]
        for index, row in enumerate(rows):
            per_batch.append({"circuit": key, "rq3": key in rq3, "batch": index, **row})
        per_circuit.append(circuit_resources(record, rows, key in rq3))

    for name, rows_out in [("resources_per_batch.csv", per_batch),
                           ("resources_per_circuit.csv", per_circuit)]:
        cols = list(rows_out[0])
        write_csv(OUT_DIR / name, cols, [[r[c] for c in cols] for r in rows_out])

    header = ["Scope", "Metric", "n", "Mean", "Min", "P25", "Median", "P75", "Max"]
    batch_metrics = [("Qubits per batch", "qubits"),
                     ("Ancillas per batch", "ancillas"),
                     ("Monitor groups per batch", "monitor_groups"),
                     ("Checkpoints per batch (= measurements = resets)", "checkpoints"),
                     ("Replay gates per batch", "replay_gates"),
                     ("2-qubit gates added per batch", "two_qubit_gates_added"),
                     ("Operation ratio (batch / original)", "ops_ratio"),
                     ("Depth ratio (batch / original)", "depth_ratio"),
                     ("2-qubit gate ratio (batch / original)", "two_qubit_ratio")]
    circuit_metrics = [("Batches B (runs per full scan)", "batches_B"),
                       ("Shots per full scan (B x 8,192)", "shots"),
                       ("QMON checkpoints K_qmon", "qmon_checkpoints_Kqmon"),
                       ("Mid-circuit checkpoints", "mid_circuit_checkpoints"),
                       ("Final reads (free)", "final_reads"),
                       ("Max qubits per batch", "max_qubits_per_batch"),
                       ("Replay gates, full scan", "replay_gates_total"),
                       ("2-qubit gates added, full scan", "two_qubit_gates_added_total"),
                       ("Max depth ratio", "depth_ratio_max"),
                       ("mu_op (Eq. 9)", "mu_op")]

    rows = []
    for scope, keep in [("All 310", lambda r: True), ("RQ3 238", lambda r: r["rq3"])]:
        rows += stat_rows([r for r in per_batch if keep(r)], batch_metrics,
                          f"{scope}, per batch")
        rows += stat_rows([r for r in per_circuit if keep(r)], circuit_metrics,
                          f"{scope}, per circuit")
    print_table(f"QMON resources before transpilation, Qmax = {QMAX}", header, rows)
    write_csv(OUT_DIR / "resources_rq2_summary.csv", header, rows)

    # Planned runs for a full scan on the 238 RQ3 circuits (paper Table IV).
    rq3_circuits = [r for r in per_circuit if r["rq3"]]
    runs_header = ["Method", "n", "Mean", "Min", "P25", "Median", "P75", "Max",
                   "Paper (mean / median / P75)"]
    runs_rows = []
    for method, field, paper in [("QMON (batches B)", "batches_B", "30.0 / 1 / 14"),
                                 ("Assertion baselines (K)", "baseline_runs_K", "92.1 / 21 / 89")]:
        values = [r[field] for r in rq3_circuits]
        runs_rows.append([method, len(values)] + [fmt(s) for s in describe(values)] + [paper])
    print_table("Planned runs per full scan, RQ3 238 circuits", runs_header, runs_rows)
    write_csv(OUT_DIR / "resources_planned_runs.csv", runs_header, runs_rows)

    print("\nTODO: baseline per-run resources (qubits, gates, depth per checkpoint circuit)"
          " not computed yet; only their run count K.")


if __name__ == "__main__":
    main()