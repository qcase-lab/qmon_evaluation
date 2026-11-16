"""Turn the authors' RQ3 record dictionaries into flat CSV rows.

Used by step04/step05 (records we produce) AND by extract_authors_results.py (records the
authors stored in results/rq3/*.pkl), so both end up in the SAME CSV columns and the same
step06 aggregation runs on either. Pure Python: no qiskit needed.

The record layout is the one built in rq3_realexec_eval.evaluate_circuit (mutant arm) and
rq3_realexec_eval.false_alarm_circuit (false-alarm arm).
"""

import common

MUTANT_FIELDS = [
    "slot_id", "circuit", "family", "seed", "ordinal", "mut_gate",
    "original_op", "replacement_op", "original_arity", "replacement_arity",
    "output_l1", "output_equivalent", "K", "K_qmon", "B",
    "in_scope_full", "in_scope_qmon", "deployment_gap", "scope_class", "plan_sha256",
]

METHOD_FIELDS = [
    "slot_id", "circuit", "seed", "method", "complete", "detected",
    "first_gate", "first_qubit", "loc_hit", "loc_precision",
    "executed_programs", "null_shortcuts",
    "mqt_run_fail", "mqt_run_unevaluable", "mqt_n_affected", "mqt_n_applicable",
]

FALSE_ALARM_FIELDS = [
    "circuit", "method", "K", "K_qmon", "B", "real_run", "complete", "execution_class",
    "n_flagged", "false_alarm", "executed_programs", "circuit_seconds",
]


def mutant_row(rec):
    """Per-mutant fields of one evaluate_circuit record."""
    return {
        "slot_id": rec["slot_id"], "circuit": rec["circuit"],
        "family": common.family_of(rec["circuit"]),
        "seed": rec["seed"], "ordinal": rec["slot_ordinal"], "mut_gate": rec["mut_gate"],
        "original_op": rec["original"]["name"], "replacement_op": rec["replacement"]["name"],
        "original_arity": rec["original"]["num_qubits"],
        "replacement_arity": rec["replacement"]["num_qubits"],
        "output_l1": rec["output_l1"],
        "output_equivalent": rec["equivalent"],                    # True -> not scored at all  [PROV:csv_equivalent]
        "K": rec["K"], "K_qmon": rec["K_qmon"], "B": rec["B"],     # plan sizes (Table IV inputs)  [PROV:csv_plan]
        "in_scope_full": rec["in_scope_full"],                     # candidate-covered  [PROV:csv_scope]
        "in_scope_qmon": rec["in_scope_qmon"],                     # deployment-covered
        "deployment_gap": rec["deployment_gap"],
        "scope_class": rec["scope_class"],
        "plan_sha256": rec["qmon_plan"]["plan_sha256"],
    }


def method_rows(rec):
    """One row per method for a non-equivalent mutant record."""
    rows = []
    for method, res in rec["methods"].items():
        stats = res.get("stats", {})
        first = res.get("first_node")
        is_mqt = method == "mqt"
        rows.append({
            "slot_id": rec["slot_id"], "circuit": rec["circuit"], "seed": rec["seed"],
            "method": method,
            "complete": res["complete"],                           # False -> excluded, never a miss  [PROV:csv_complete]
            "detected": res["detected"],                           # True = caught (TP), False = missed (FN)  [PROV:csv_detected]
            "first_gate": first[0] if first else None,             # earliest flagged checkpoint
            "first_qubit": first[1] if first else None,
            "loc_hit": res["loc_hit"],                             # mutated gate inside its cone?
            "loc_precision": res["loc_precision"],                 # 1/|cone| or 0  [PROV:csv_loc]
            "executed_programs": res.get("executed_program_count"),
            "null_shortcuts": stats.get("n_null_shortcuts"),
            "mqt_run_fail": stats.get("run_fail", 0) if is_mqt else None,              # evaluated mismatch  [PROV:csv_mqt]
            "mqt_run_unevaluable": stats.get("run_unevaluable", 0) if is_mqt else None,  # refusal
            "mqt_n_affected": stats.get("n_affected") if is_mqt else None,
            "mqt_n_applicable": stats.get("n_applicable") if is_mqt else None,
        })
    return rows


def false_alarm_rows(record, seconds=None):
    """One row per method for one false_alarm_circuit record."""
    rows = []
    for method, res in record["methods"].items():
        rows.append({
            "circuit": record["circuit"], "method": method,
            "K": record["K"], "K_qmon": record["K_qmon"], "B": record["B"],
            "real_run": record["real_run"],                       # baselines executed (K <= 200)?
            "complete": res["complete"],
            "execution_class": res["execution_class"],             # physical / counterfactual / exact-null / definition-shortcut
            "n_flagged": res["n_flagged"],                         # flagged checkpoints on a CORRECT circuit
            "false_alarm": res["false_alarm"],                     # True = false positive, False = true negative  [PROV:csv_false_alarm]
            "executed_programs": res["n_executed_programs"],
            "circuit_seconds": seconds,
        })
    return rows
