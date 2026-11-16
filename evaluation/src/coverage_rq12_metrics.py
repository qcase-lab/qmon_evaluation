import csv                           # write the output tables
import math                          # ceil() for nearest-rank percentiles
import statistics                    # mean, median
import sys                           # edit the import path
from pathlib import Path             # file paths

REPO = Path(__file__).resolve().parents[1]          # extension/ -> repo root
sys.path.insert(0, str(REPO / "src"))               # so the authors' modules import

from qiskit import QuantumCircuit
from entanglement_disturbance import resolve_circuit_corpus, DEFAULT_MANIFEST, DEFAULT_QASM_DIR
from rq1_certificate_check import crosscheck_selector                 # Algorithm 1 (+ recheck)
from coverage_rq2 import (
    QMAX,                     # 24: qubit budget per instrumented run
    _build_operation_list,    # Algorithm 2 + final-read split
    _group_demands,           # grouping + ancilla accounting + FFD/ILP packing
    _emit_batches,            # builds the batch circuits
    gate_layers,              # ASAP layers -> circuit depth
)
from fast_analysis import SKIP_OPS                                    # non-gate operations

OUT_DIR = REPO / "outputs"


def circuit_metrics(key, qasm_dir):
    """Every coverage metric for ONE circuit, computed the way the authors do it."""
    qc = QuantumCircuit.from_qasm_file(str(qasm_dir / key))

    # ---- Step 1: Algorithm 1 ------------------------------------------------
    # Simulates the circuit gate by gate; after each gate, tests whether each qubit
    # it touched is separable from the rest (second Schmidt amplitude <= 1e-12).
    check = crosscheck_selector(qc)
    all_points = check["all_points"]            # one row per gate-qubit location
    selected_rows = check["selected_points"]    # the locations that passed = candidates

    # Gate-qubit locations: every (gate, qubit) pair where the gate acts on the qubit.
    # A 1-qubit gate gives 1 location, a 2-qubit gate gives 2.
    locations = {(r["gate"], r["qubit"]) for r in all_points}
    # Numerical candidates: the locations where monitoring is safe.
    candidates = {(r["gate"], r["qubit"]) for r in selected_rows}
    # Gates (not measurements/barriers), for gate coverage.
    gate_count = sum(inst.operation.name not in SKIP_OPS for inst in qc.data)

    # ---- Step 2: Algorithm 2 ------------------------------------------------
    # Traces each candidate's backward causal cone (the gates to replay).
    # final_reads = candidates at a qubit's last gate before the final measurement:
    #               read for free, no mid-circuit monitor needed.
    # prebudget   = the remaining candidates, which need a mid-circuit monitor.
    operation_list, prebudget, final_reads = _build_operation_list(qc, key, selected_rows)

    # ---- Step 3: grouping, ancillas, packing at Qmax = 24 -------------------
    # Checkpoints after the same gate form one group sharing one replay. Each group
    # needs some ancillas; groups are packed into batches so that
    # original qubits + ancillas <= 24. A group too big even alone is dropped.
    group_demands, batches, infeasible_gates, _ = _group_demands(
        qc, key, operation_list, prebudget)

    # ---- Step 4: build the batch circuits -------------------------------------
    # emitted = the mid-circuit checkpoints actually instrumented in some batch.
    emitted, _ = _emit_batches(qc, key, operation_list, group_demands, batches)

    # Deployed checkpoints = instrumented mid-circuit checkpoints + free final reads.
    deployed = emitted | final_reads
    deployed_gates = {gate for gate, _ in deployed}
    deployed_qubits = {qubit for _, qubit in deployed}

    # ---- Step 5: layers, for depth reach ----------------------------------------
    # Each gate sits in the earliest layer after the latest gate on its qubits;
    # depth = number of layers.
    layers, depth = gate_layers(qc)

    # ---- The metrics (the authors' formulas) ------------------------------------
    return {
        "circuit": key,
        "num_qubits": qc.num_qubits,
        "gates": gate_count,
        "locations": len(locations),
        "candidates": len(candidates),
        "deployed": len(deployed),
        "batches": len(batches),
        "dropped_groups": len(infeasible_gates),
        # RQ1: candidates / locations, for this circuit
        "candidate_rate": len(candidates) / len(locations),
        # RQ2: deployed checkpoints / locations, for this circuit
        "deployed_location_coverage": len(deployed) / len(locations),
        # RQ2: gates with at least one deployed checkpoint / gates (= paper's 44.54% mean)
        "deployed_gate_coverage": len(deployed_gates) / gate_count,
        # RQ2: qubits with at least one deployed checkpoint / qubits
        "qubit_coverage": len(deployed_qubits) / qc.num_qubits,
        # RQ2: layer of the deepest deployed checkpoint / circuit depth
        "depth_reach": (max((layers[g] for g in deployed_gates), default=0) / depth
                        if depth else 0.0),
        # RQ2: every qubit has at least one deployed checkpoint
        "full_qubit_coverage": len(deployed_qubits) == qc.num_qubits,
    }


def describe(values):
    """mean, min, p25, median, p75, max of a list of numbers."""
    v = sorted(values)
    n = len(v)
    rank = lambda p: v[max(math.ceil(p * n), 1) - 1]          # nearest-rank percentile
    return [statistics.mean(v), v[0], rank(0.25), statistics.median(v), rank(0.75), v[-1]]


def write_csv(path, header, rows):
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main():
    # The authors' circuit list, in their order, with file hashes checked.
    frame = resolve_circuit_corpus(DEFAULT_MANIFEST, DEFAULT_QASM_DIR)
    qasm_dir = Path(frame["qasm_dir"])

    per_circuit = []
    for i, entry in enumerate(frame["circuits"], start=1):
        print(f"[{i}/{frame['circuit_count']}] {entry['circuit']}", flush=True)
        per_circuit.append(circuit_metrics(entry["circuit"], qasm_dir))
    n = len(per_circuit)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cols = list(per_circuit[0])
    write_csv(OUT_DIR / "coverage_rq12_per_circuit.csv", cols,
              [[r[c] for c in cols] for r in per_circuit])

    # ---- Summary table ------------------------------------------------------------
    header = ["Metric", "Mean", "Min", "P25", "Median", "P75", "Max", "Paper"]
    rows = []
    for label, field, paper in [
        ("Numerical-candidate rate (per circuit)", "candidate_rate", "-"),
        ("Deployed location coverage", "deployed_location_coverage", "44.54% (see note)"),
        ("Deployed gate coverage", "deployed_gate_coverage", "-"),
        ("Qubit coverage", "qubit_coverage", "89.75%"),
        ("Normalized depth reach", "depth_reach", "48.57%"),
    ]:
        stats = describe([r[field] for r in per_circuit])      # one value per circuit
        rows.append([label] + [f"{100 * s:.2f}%" for s in stats] + [paper])

    # Pooled rate: ALL candidates / ALL locations, every circuit thrown together.
    cand = sum(r["candidates"] for r in per_circuit)
    locs = sum(r["locations"] for r in per_circuit)
    rows.append(["Pooled numerical-candidate rate",
                 f"{cand:,} / {locs:,} = {100 * cand / locs:.2f}%", "", "", "", "", "", "39.61%"])

    full = sum(r["full_qubit_coverage"] for r in per_circuit)
    rows.append(["Circuits with full qubit coverage",
                 f"{full} / {n} ({100 * full / n:.2f}%)", "", "", "", "", "", "254 / 310"])

    widths = [max(len(str(r[i])) for r in [header] + rows) for i in range(len(header))]
    line = lambda r: "  ".join(str(c).ljust(w) for c, w in zip(r, widths))
    print(f"\nRQ1/RQ2 coverage, {n} circuits, Qmax = {QMAX}\n")
    print(line(header))
    print("  ".join("-" * w for w in widths))
    for r in rows:
        print(line(r))
    print("\nNote: the paper defines its 44.54% as deployed checkpoints / gate-qubit locations,"
          "\nbut 44.54% is the mean of deployed GATE coverage; location coverage is 40.68%.")
    write_csv(OUT_DIR / "coverage_rq12_metrics.csv", header, rows)


if __name__ == "__main__":
    main()