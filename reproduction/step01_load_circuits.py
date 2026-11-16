"""STEP 01 - Load the 310 MQT Bench circuits and record their basic structure.

Run from anywhere (venv with the authors' requirements active):

    python reproduction/step01_load_circuits.py

Input : inputs/certified_circuits.txt (310 names) and quantum_circuits/*.qasm
Output: reproduction/data/step01_circuits.csv - one row per circuit

Why this step exists: every later step reads circuits the same way the authors do
(QuantumCircuit.from_qasm_file on quantum_circuits/<name>.qasm) and keys them by the
file name WITH ".qasm". This step checks that all 310 files load and records the
numbers the paper uses to describe the corpus (2-14 qubits, gate counts, depth).
"""

import time                                          # time each load (sanity only)

import common                                        # our shared paths/helpers
common.use_authors_code()                            # put the authors' src/ on the import path

from qiskit import QuantumCircuit                    # the same loader the authors use
from fast_analysis import SKIP_OPS                   # authors' list of NON-gate operations
from coverage_rq2 import gate_layers                 # authors' ASAP depth (paper Sec. VI-B)


def describe(key):
    """Load one circuit and count what the paper counts."""
    started = time.perf_counter()                                 # start a timer
    qc = QuantumCircuit.from_qasm_file(str(common.CIRCUIT_DIR / key))  # parse the QASM file
    load_seconds = time.perf_counter() - started                  # how long parsing took

    ops = [ci.operation for ci in qc.data]                        # every instruction in program order
    gates = [op for op in ops if op.name not in SKIP_OPS]         # unitary gates only (no measure/barrier/reset)
    one_q = sum(op.num_qubits == 1 for op in gates)               # N1 in the paper's two-qubit-density formula
    two_q = sum(op.num_qubits == 2 for op in gates)               # N2
    wider = sum(op.num_qubits > 2 for op in gates)                # should be 0: circuits are pre-decomposed
    # Gate-qubit locations = one per (gate, qubit acted on): 1q gate -> 1, 2q gate -> 2.
    locations = sum(op.num_qubits for op in gates)                # denominator of RQ2 location coverage
    _, depth = gate_layers(qc)                                    # ASAP layer count (authors' function)
    return {
        "circuit": key,                                           # file name, the key every step uses
        "family": common.family_of(key),                          # authors' family label (42 families)
        "n_qubits": qc.num_qubits,                                # Qbase in the batching budget
        "n_clbits": qc.num_clbits,
        "n_instructions": len(ops),                               # includes measure/barrier
        "n_unitary_gates": len(gates),                            # m in the paper
        "n_1q_gates": one_q,
        "n_2q_gates": two_q,
        "n_wider_gates": wider,
        "n_measurements": sum(op.name == "measure" for op in ops),
        "n_gate_qubit_locations": locations,
        "asap_depth": depth,
        "two_qubit_density": (two_q / len(gates)) if gates else None,  # delta_2 = N2/(N1+N2)
        "load_seconds": round(load_seconds, 4),
    }


def main():
    all_keys = common.read_names(common.ALL_CIRCUITS_LIST)        # the 310 RQ1/RQ2 circuits
    rq3_keys = set(common.read_names(common.RQ3_CIRCUITS_LIST))   # the 238-circuit RQ3 subset
    rows = []
    for index, key in enumerate(all_keys, start=1):
        row = describe(key)                                       # load + count
        row["in_authors_rq3_list"] = key in rq3_keys              # is it one of the 238?
        rows.append(row)
        print(f"[{index}/{len(all_keys)}] {key}: {row['n_qubits']} qubits, "
              f"{row['n_unitary_gates']} gates", flush=True)
    out = common.write_csv(common.DATA / "step01_circuits.csv", rows, list(rows[0].keys()))
    print(f"wrote {out} ({len(rows)} circuits; "
          f"{sum(r['in_authors_rq3_list'] for r in rows)} in the RQ3 list)")


if __name__ == "__main__":
    main()
