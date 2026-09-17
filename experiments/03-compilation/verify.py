#!/usr/bin/env python3
"""Vérifications indépendantes de la mesure.

1. Plan complet : chaque processus prévu a produit toutes ses lignes, avec le
   binaire attendu (le binaire écrit lui-même son compilateur et son niveau).
2. Épinglage respecté : tous les échantillons sur le CPU prévu.
3. Résultats exacts : le harnais compare déjà chaque résultat à sa valeur
   attendue ; ici, les valeurs attendues sont recalculées indépendamment en
   Python (``--replay``, tailles modestes) et doivent être identiques pour tous
   les binaires à taille égale.
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path

MASK = (1 << 64) - 1


def splitmix64(value):
    value = (value + 0x9E3779B97F4A7C15) & MASK
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK
    return value ^ (value >> 31)


def expected_per_call(label, n, seed, cache):
    if label in ("sum_array", "sum_array_bis", "sum_array_twice"):
        if (seed, n) not in cache:
            cache[(seed, n)] = sum(splitmix64(seed + i) for i in range(n)) & MASK
        return (cache[(seed, n)] * (2 if label == "sum_array_twice" else 1)) & MASK
    if label == "sum_discarded":
        return 0
    return (n * (n - 1) // 2) & MASK


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--replay", action="store_true")
    args = parser.parse_args()

    with (args.directory / "plan.csv").open(newline="", encoding="utf-8") as source:
        plan = list(csv.DictReader(source))
    errors = []
    expected_by_key = defaultdict(set)
    cache = {}
    for planned in plan:
        run_id = int(planned["run_id"])
        path = args.directory / f"run-{run_id:03d}.csv"
        meta_path = args.directory / f"run-{run_id:03d}-meta.csv"
        if not path.exists() or not meta_path.exists():
            errors.append(f"processus {run_id} : fichier absent")
            continue
        with path.open(newline="", encoding="utf-8") as source:
            rows = list(csv.DictReader(source))
        sizes = (int(planned["max_log2"]) - int(planned["min_log2"])) // int(planned["step_log2"]) + 1
        if len(rows) != sizes * 5 * int(planned["rounds"]):
            errors.append(f"processus {run_id} : {len(rows)} lignes inattendues")
        level = f"{planned['compiler']}-{planned['level']}"
        if any(row["level"] != level for row in rows):
            errors.append(f"processus {run_id} : le binaire ne déclare pas {level}")
        cpu = planned["cpu"]
        if any(row["cpu_before"] != cpu or row["cpu_after"] != cpu for row in rows):
            errors.append(f"processus {run_id} : épinglage sur le CPU {cpu} non respecté")
        for row in rows:
            if row["result"] != row["expected"]:
                errors.append(f"processus {run_id} : résultat inexact ({row['label']}, n={row['n']})")
                break
            expected_by_key[(row["label"], row["n"], row["calls"])].add(row["expected"])
            if args.replay:
                value = (int(row["calls"]) * expected_per_call(
                    row["label"], int(row["n"]), int(row["seed"]), cache)) & MASK
                if value != int(row["expected"]):
                    errors.append(f"processus {run_id} : valeur attendue non reproduite en Python")
                    break
    divergent = [key for key, values in expected_by_key.items() if len(values) != 1]
    if divergent:
        errors.append(f"{len(divergent)} couples (noyau, taille) avec des résultats différents selon le binaire")
    if errors:
        raise SystemExit("\n".join(errors[:20]))
    replayed = ", valeurs attendues recalculées en Python" if args.replay else ""
    print(f"vérification : {len(plan)} processus complets, résultats exacts et identiques "
          f"pour tous les binaires{replayed}, OK")


if __name__ == "__main__":
    main()
