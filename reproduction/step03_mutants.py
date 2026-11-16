"""STEP 03 - The mutant set (single-gate faults) for RQ3.

Two modes, same output format:

    # (a) the authors' fixed 3,570 mutants (seeds 1-5) -> exact reproduction
    python reproduction/step03_mutants.py --tag authors

    # (b) OUR mutants: the authors' generator with new seeds (default 6-10)
    python reproduction/step03_mutants.py --tag ours --seeds 6 7 8 9 10

Outputs (reproduction/data/):
  mutants_<tag>.json - a mutation manifest in the authors' schema (for tag=authors it is a
                       verified copy of inputs/rq3_single_error_manifest.json)
  mutants_<tag>.csv  - one row per mutant: circuit, seed, ordinal, mutated gate, original and
                       replacement operation, output L1 distance, output-equivalent flag

How the authors draw mutants (rq3_manifest.build_manifest, paper App. B-B(a)):
  * candidates = 1q/2q unitary gate indices <= the last Algorithm-1 candidate gate;
  * per (circuit, seed): random.seed(seed); pick 3 distinct gates with random.sample;
  * mutate_circuit() replaces each picked gate by a random same-arity gate
    (1q: rx, ry, x, y, h; 2q: cp, rzx, rzz, cx, cz; angles uniform in [0, 2*pi]),
    redrawing if the replacement equals the original;
  * output-equivalent = L1 distance of the exact final measured-output distributions < 1e-9.
We call exactly those functions; only the seed list changes for tag=ours.
"""

import argparse
import json
import random                                        # the authors seed Python's global RNG

import numpy as np

import common
common.use_authors_code()

from qiskit import QuantumCircuit
import rq3_manifest                                  # authors' manifest builder/validator
from rq3_manifest import (load_manifest, validate_manifest, save_manifest,
                          operation_signature, circuit_qasm_sha256, stable_hash,
                          runtime_fingerprints, SLOTS_PER_SEED, OUTPUT_EQ_L1)
from mutation import mutate_circuit                  # the replacement operator
from rq3_eval import final_probs, monitored_nodes, unitary_gate_indices
from utilities import quantum_gates                  # gate menu used by mutate_circuit


def build_manifest_for_seeds(keys, seeds):
    """Line-for-line copy of rq3_manifest.build_manifest with a configurable seed list.
    (Their function hard-codes SEEDS=(1..5) and refuses non-canonical counts.)"""
    protocol = dict(rq3_manifest.PROTOCOL)                        # authors' protocol description
    protocol["seeds"] = list(seeds)                               # the only change: our seeds
    slots, circuit_entries = [], []
    for key in keys:
        qc = QuantumCircuit.from_qasm_file(str(common.CIRCUIT_DIR / key))
        nodes = monitored_nodes(qc)                               # Algorithm-1 candidates
        last_node = max(index for index, _ in nodes)              # last candidate gate index
        candidates = [g for g in unitary_gate_indices(qc) if g <= last_node]   # [PROV:mutant_candidates]
        measured = [qc.find_bit(ci.qubits[0]).index               # qubits with terminal measurement
                    for ci in qc.data if ci.operation.name == "measure"]
        base_probs = final_probs(qc, measured)                    # exact original output distribution
        source_hash = circuit_qasm_sha256(qc)
        circuit_entries.append({"circuit": key, "source_qasm_sha256": source_hash,
                                "candidate_count": len(candidates),
                                "last_monitorable_gate": int(last_node)})
        for seed in seeds:
            random.seed(seed)                                     # [PROV:mutant_seed] one reseed per (circuit, seed)
            gates = random.sample(candidates, SLOTS_PER_SEED)     # 3 distinct gates, no replacement
            for ordinal, gate in enumerate(gates):
                original = operation_signature(qc, gate)          # name/params/qubits before
                mutant = mutate_circuit(qc, gate, quantum_gates)  # [PROV:mutant_replace] same RNG stream continues
                replacement = operation_signature(mutant, gate)   # name/params/qubits after
                if replacement == original:                       # authors' guard against no-op mutants
                    raise AssertionError(f"no-op mutation {key}/s{seed}/{ordinal}")
                mutant_probs = final_probs(mutant, measured)      # exact mutant output distribution
                l1 = (float(np.abs(base_probs - mutant_probs).sum())
                      if len(base_probs) == len(mutant_probs) else None)
                slots.append({
                    "slot_id": f"{key}|s{seed}|m{ordinal}",       # unique mutant id
                    "circuit": key, "seed": int(seed), "ordinal": int(ordinal), "gate": int(gate),
                    "source_qasm_sha256": source_hash,
                    "original": original, "replacement": replacement,
                    "mutant_qasm_sha256": circuit_qasm_sha256(mutant),
                    "output_equivalent": bool(l1 is not None and l1 < OUTPUT_EQ_L1),  # [PROV:mutant_equivalent]
                    "output_l1": l1,
                })
    equivalent = sum(s["output_equivalent"] for s in slots)
    manifest = {
        "schema": rq3_manifest.SCHEMA,
        "protocol": protocol,
        "fingerprints": runtime_fingerprints(protocol, keys=keys),
        "circuits": circuit_entries,
        "counts": {"circuits": len(keys), "slots": len(slots),
                   "output_equivalent": equivalent,
                   "non_output_equivalent": len(slots) - equivalent},
        "slots": slots,
    }
    manifest["manifest_sha256"] = stable_hash(manifest)           # content hash, as the authors do
    validate_manifest(manifest, require_canonical_counts=False)   # authors' structural checks
    return manifest


def load_any_manifest(path):
    """Load a manifest written by this script (any seeds) with the authors' structural checks.
    For the canonical file use rq3_manifest.load_manifest (it also checks checksums)."""
    with open(path, "rb") as handle:
        manifest = json.load(handle)
    return validate_manifest(manifest, require_canonical_counts=False, verify_runtime=False)


def manifest_rows(manifest):
    rows = []
    for s in manifest["slots"]:
        rows.append({
            "slot_id": s["slot_id"], "circuit": s["circuit"],
            "family": common.family_of(s["circuit"]),
            "seed": s["seed"], "ordinal": s["ordinal"], "mut_gate": s["gate"],
            "original_op": s["original"]["name"], "replacement_op": s["replacement"]["name"],
            "original_arity": s["original"]["num_qubits"],
            "replacement_arity": s["replacement"]["num_qubits"],
            "replacement_params": s["replacement"]["params"],
            "output_l1": s["output_l1"],
            "output_equivalent": bool(s["output_equivalent"]),     # True -> excluded from detection
        })
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True, help="'authors' or a name for your own set, e.g. 'ours'")
    parser.add_argument("--seeds", type=int, nargs="+", default=list(common.OUR_SEEDS))
    args = parser.parse_args()

    if args.tag == "authors":
        manifest = load_manifest(common.CANONICAL_MANIFEST)       # authors' file + checksum/replay checks
    else:
        if set(args.seeds) & set(common.AUTHOR_SEEDS):
            print("warning: some seeds overlap the authors' seeds 1-5; those mutants are identical")
        keys = common.read_names(common.RQ3_CIRCUITS_LIST)        # same 238 circuits
        manifest = build_manifest_for_seeds(keys, args.seeds)

    json_path = common.DATA / f"mutants_{args.tag}.json"
    save_manifest(manifest, json_path)                            # authors' atomic writer
    rows = manifest_rows(manifest)
    common.write_csv(common.DATA / f"mutants_{args.tag}.csv", rows, list(rows[0].keys()))
    print(f"{args.tag}: {manifest['counts']} -> {json_path}")


if __name__ == "__main__":
    main()
