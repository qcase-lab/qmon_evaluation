"""STEP 02 - Algorithm 1 (candidate selection), Algorithm 2 (backward causal cones),
and the Qmax=24 deployment plan (grouping + FFD/ILP batching) for every circuit.

    python reproduction/step02_alg1_alg2.py                 # all 310 circuits
    python reproduction/step02_alg1_alg2.py --only rq3      # just the 238 RQ3 circuits
    python reproduction/step02_alg1_alg2.py --check-dfs     # also cross-check Alg. 2 implementations

Set QMON_MILP_SOLVER=gurobi to get the authors' exact batch counts (CBC may pack
some large circuits differently).

Outputs (reproduction/data/):
  step02_locations.csv - one row per gate-qubit location (56,386 for the 310 circuits):
                         Alg. 1 verdict, expected p1, final-read flag, deployed flag, cone size
  step02_plans.csv     - one row per circuit: candidate counts, K, K_qmon, B, RQ3 eligibility,
                         and how long each stage took (useful for the runtime contribution)

What feeds RQ3: the RQ3 evaluator rebuilds exactly these objects inside its
`Oracle` class (rq3_realexec_eval.py). We call the same functions here so the
per-circuit numbers RQ3 relies on (checkpoint set K, deployed set K_qmon, batches B,
expected p1 per checkpoint, cone of every checkpoint) are visible as data.
"""

import argparse                                      # command-line options
import time                                          # stage timings

import common
common.use_authors_code()                            # authors' src/ on the path

from qiskit import QuantumCircuit
from fast_analysis import analyze_per_gate_nolock    # ALGORITHM 1 (a2 <= 1e-12 test after each gate)
from circuits_selection import (standard_final_read_nodes,   # candidates read by the existing final measure
                                dfs_quantum_circuit)         # ALGORITHM 2 as used to build replay lists
from mps_analysis import causal_cone                 # ALGORITHM 2 as a gate SET (used for RQ3 scope/localization)
from rq3_eval import unitary_gate_indices            # mutable gates (1q/2q unitaries)
from rq3_realexec_eval import Oracle                 # authors' RQ3 per-circuit plan builder


def flatten_dfs(path):
    """dfs_quantum_circuit returns a nested list; collect every gate index in it."""
    found = set()
    for entry in path:                                # entry = [index, name, params, qubits(, subpath)]
        found.add(int(entry[0]))                      # the gate itself
        if len(entry) > 4:                            # a two-qubit gate carries the other wire's subpath
            found |= flatten_dfs(entry[4])            # recurse into the branch
    return found


def analyse(key, check_dfs=False):
    qc = QuantumCircuit.from_qasm_file(str(common.CIRCUIT_DIR / key))   # same loader as step 01

    # ---------------- ALGORITHM 1: numerical candidates --------------------------------------
    t0 = time.perf_counter()
    res, _, paths = analyze_per_gate_nolock(qc)       # one statevector pass; res[i] rows = [i, name, q, p0, p1]
    alg1_seconds = time.perf_counter() - t0
    # paths[q] = gate indices where qubit q passed the separability test -> candidate (i, q)
    candidates = {(int(i), int(q)) for q in paths for i in paths[q]}
    # every gate-qubit location (the RQ2 denominator) with its exact p0/p1 after gate i
    locations = {(int(r[0]), int(r[2])): r for i in res for r in res[i]}

    # Final-read exclusion (paper Sec. IV-B): a candidate that is the last gate before the
    # qubit's terminal measurement gets no extra mid-circuit monitor; the final read observes it.
    final_reads = standard_final_read_nodes(qc, candidates)

    # ---------------- ALGORITHM 2: backward causal cone of every candidate ---------------------
    t1 = time.perf_counter()
    cones = {node: causal_cone(qc, node[0], node[1]) for node in candidates}  # (gate set, qubit set)
    alg2_seconds = time.perf_counter() - t1
    dfs_mismatches = 0
    if check_dfs:                                     # optional: Alg. 2 via the replay DFS must give the same gates
        for (i, q) in candidates:
            if flatten_dfs(dfs_quantum_circuit(qc, q, i, set(), [])) != cones[(i, q)][0]:
                dfs_mismatches += 1

    # ---------------- Deployment plan at Qmax = 24 (grouping + FFD + conditional ILP) ----------
    # Oracle(key) re-runs Alg. 1, rebuilds the replay lists with dfs_quantum_circuit, groups
    # same-gate candidates, computes ancilla demands and calls batch_partition.partition_nodes.
    t2 = time.perf_counter()
    plan_error = None
    try:
        oracle = Oracle(key, common.QMAX)
    except Exception as exc:                          # e.g. no plan can be built
        oracle, plan_error = None, f"{type(exc).__name__}: {exc}"
    plan_seconds = time.perf_counter() - t2
    if oracle is not None and (not oracle.nodes or getattr(oracle, "B", None) is None):
        oracle, plan_error = None, "no candidates or no deployment plan"   # Oracle stops early here

    deployed = set(oracle.qmon_nodes) if oracle else set()   # QMON's checkpoint set (K_qmon of them)
    if oracle is not None:
        assert set(oracle.nodes) == candidates, f"{key}: Oracle nodes != Algorithm 1 candidates"

    # RQ3 eligibility (paper Sec. VI-C): has a plan, the last candidate is beyond the first layer,
    # and at least three mutable gates lie at or before the last candidate.
    last_candidate = max((i for i, _ in candidates), default=None)
    mutable = ([g for g in unitary_gate_indices(qc) if g <= last_candidate]
               if last_candidate is not None else [])
    rq3_eligible = bool(oracle is not None and oracle.eligible() and len(mutable) >= 3)

    location_rows = []
    for (i, q), r in sorted(locations.items()):
        node = (i, q)
        location_rows.append({
            "circuit": key, "gate": i, "qubit": q, "gate_name": r[1],
            "p0": float(r[3]), "p1": float(r[4]),                 # expected outcome probabilities
            "candidate": node in candidates,                       # passed Algorithm 1
            "final_read": node in final_reads,                     # observed by the terminal measurement
            "deployed": node in deployed,                          # in QMON's Qmax=24 checkpoint set
            "cone_gates": len(cones[node][0]) if node in cones else None,   # |Cone| (localization denominator)
            "cone_qubits": len(cones[node][1]) if node in cones else None,  # wires the replay touches
        })

    plan = {
        "circuit": key,
        "n_qubits": qc.num_qubits,
        "n_locations": len(locations),                             # gate-qubit locations
        "n_candidates": len(candidates),                           # = K for the assertion baselines
        "n_final_read_candidates": len(final_reads),
        "n_mid_candidates": len(candidates - final_reads),         # need a measure-reset-replay monitor
        "K": oracle.K if oracle else len(candidates),
        "K_qmon": oracle.K_qmon if oracle else None,               # deployed QMON checkpoints
        "B": oracle.B if oracle else None,                         # batches = planned QMON runs
        "n_cannot_fit_groups": len(oracle.infeasible) if oracle else None,
        "batch_costs": [b["cost"] for b in oracle.batches] if oracle and oracle.batches else None,
        "last_candidate_gate": last_candidate,
        "n_mutable_gates_upto_last_candidate": len(mutable),
        "rq3_eligible": rq3_eligible,
        "plan_sha256": oracle.qmon_plan["plan_sha256"] if oracle else None,
        "plan_error": plan_error,
        "dfs_cone_mismatches": dfs_mismatches if check_dfs else None,
        "alg1_seconds": round(alg1_seconds, 4),
        "alg2_cone_seconds": round(alg2_seconds, 4),
        "plan_seconds": round(plan_seconds, 4),
    }
    return location_rows, plan


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=["all", "rq3"], default="all")
    parser.add_argument("--check-dfs", action="store_true")
    args = parser.parse_args()

    keys = common.read_names(common.ALL_CIRCUITS_LIST if args.only == "all"
                             else common.RQ3_CIRCUITS_LIST)
    authors_rq3 = set(common.read_names(common.RQ3_CIRCUITS_LIST))
    all_locations, plans = [], []
    for index, key in enumerate(keys, start=1):
        rows, plan = analyse(key, args.check_dfs)
        plan["in_authors_rq3_list"] = key in authors_rq3
        all_locations.extend(rows)
        plans.append(plan)
        print(f"[{index}/{len(keys)}] {key}: K={plan['K']} K_qmon={plan['K_qmon']} "
              f"B={plan['B']} rq3_eligible={plan['rq3_eligible']}", flush=True)

    common.write_csv(common.DATA / "step02_locations.csv", all_locations, list(all_locations[0].keys()))
    common.write_csv(common.DATA / "step02_plans.csv", plans, list(plans[0].keys()))
    disagree = [p["circuit"] for p in plans if p["rq3_eligible"] != p["in_authors_rq3_list"]]
    print(f"RQ1 check: {sum(r['candidate'] for r in all_locations)} candidates / "
          f"{len(all_locations)} locations (paper: 22,332 / 56,386 for all 310)")
    print(f"RQ3 eligibility disagrees with inputs/rq3_circuits.txt for {len(disagree)} circuits: "
          f"{disagree[:10]}")


if __name__ == "__main__":
    main()
