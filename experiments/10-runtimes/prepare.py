#!/usr/bin/env python3
"""Prépare une campagne E2 : plan des processus des parties 2 (échauffement) et 3
(allocation), mélangés dans un ordre aléatoire fixé avant la première mesure.

Chaque ligne fixe le mode (environnement d'exécution et ses options) et les CPU autorisés.
La partie 1 (démarrage) est lancée par run.sh après les processus du plan.
"""

import argparse
import csv
import random
from pathlib import Path

BASE_SEED = 20260923
WARM_MODES = {   # mode : CPU autorisés
    "c": "11", "java": "11", "java-xint": "11", "java-2cpu": "9;11",
    "node": "11", "node-jitless": "11", "node-2cpu": "9;11",
    "python": "11", "python-jit": "11",
}
CHURN_MODES = ("c", "go-gogc100", "go-gogc400", "java-g1", "java-serial", "node", "python-gc", "python-nogc")
SETTINGS = {
    "check": {"runs": 1, "steps": 3, "n_log2": 10, "live_log2": 10, "batch_log2": 8, "batches": 16,
              "startup_reps": 2, "decomposition_reps": 2},
    "quick": {"runs": 1, "steps": 60, "n_log2": 16, "live_log2": 20, "batch_log2": 13, "batches": 256,
              "startup_reps": 5, "decomposition_reps": 3},
    "campaign": {"runs": 10, "steps": 300, "n_log2": 16, "live_log2": 20, "batch_log2": 13, "batches": 1024,
                 "startup_reps": 50, "decomposition_reps": 20},
}
FIELDS = ["run_id", "part", "mode", "cpus", "steps", "n_log2", "live_log2", "batch_log2", "batches"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=sorted(SETTINGS))
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    s = SETTINGS[args.mode]
    plan = [{"part": "warm", "mode": m, "cpus": c} for m, c in WARM_MODES.items() for _ in range(s["runs"])]
    plan += [{"part": "churn", "mode": m, "cpus": "11"} for m in CHURN_MODES for _ in range(s["runs"])]
    random.Random(BASE_SEED).shuffle(plan)
    for run_id, row in enumerate(plan, start=1):
        row.update({"run_id": run_id, **{k: s[k] for k in FIELDS if k in s}})
    args.directory.mkdir(parents=True, exist_ok=True)
    with (args.directory / "plan.csv").open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(plan)
    (args.directory / "startup-reps.txt").write_text(f"{s['startup_reps']} {s['decomposition_reps']}\n")
    print(f"plan={args.directory / 'plan.csv'} processes={len(plan)}")


if __name__ == "__main__":
    main()
