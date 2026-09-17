#!/usr/bin/env python3
"""Vérifications indépendantes de la mesure.

1. Le plan est complet : chaque processus prévu a produit toutes ses lignes.
2. L'épinglage demandé a bien été appliqué (un seul CPU autorisé, le bon).
3. Avec ``--replay``, le calcul est rejoué en Python à partir de la graine :
   chaque ligne doit contenir le résultat exact après ``ops × calls_per_op``
   appels. Cela prouve que le travail chronométré a réellement été exécuté,
   sans supposer quoi que ce soit du compilateur.
"""

import argparse
import csv
from pathlib import Path

MASK = (1 << 64) - 1
GOLDEN = 0x9E3779B97F4A7C15
MULTIPLIER = 2685821657736338717
# Appels à tiny_work effectués par l'amorçage, avant la première mesure.
PRIME_CALLS = {"none": 0, "clock": 0, "code": 3, "full": 4}


def tiny_work(value):
    value ^= value >> 12
    value ^= (value << 25) & MASK
    value ^= value >> 27
    return (value * MULTIPLIER) & MASK


def expected_rows(plan_row):
    rounds = int(plan_row["rounds"])
    if plan_row["mode"] == "amortization":
        sizes = int(plan_row["max_batch"]).bit_length()
        return sizes * rounds
    return 3 * rounds


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--replay", action="store_true")
    args = parser.parse_args()

    with (args.directory / "plan.csv").open(newline="", encoding="utf-8") as source:
        plan = list(csv.DictReader(source))
    errors = []
    for planned in plan:
        run_id = int(planned["run_id"])
        path = args.directory / f"run-{run_id:03d}.csv"
        if not path.exists() or not (args.directory / f"run-{run_id:03d}-meta.csv").exists():
            errors.append(f"processus {run_id} : fichier absent")
            continue
        with path.open(newline="", encoding="utf-8") as source:
            rows = list(csv.DictReader(source))
        if len(rows) != expected_rows(planned):
            errors.append(f"processus {run_id} : {len(rows)} lignes, {expected_rows(planned)} attendues")
        if any(row["protocol"] != planned["protocol"] for row in rows):
            errors.append(f"processus {run_id} : protocole différent du plan")
        if planned["cpu"]:
            pinned = int(planned["cpu"])
            if any(int(row["allowed_cpus"]) != 1 or int(row["cpu_before"]) != pinned
                   or int(row["cpu_after"]) != pinned for row in rows):
                errors.append(f"processus {run_id} : épinglage sur le CPU {pinned} non respecté")
        if args.replay and rows:
            first = rows[0]
            state = int(first["seed"]) ^ ((run_id * GOLDEN) & MASK)
            state = state or GOLDEN
            for _ in range(int(first["warmup_ops"]) + PRIME_CALLS[first.get("prime", "none")]):
                state = tiny_work(state)
            for row in sorted(rows, key=lambda item: int(item["sample"])):
                for _ in range(int(row["ops"]) * int(row["calls_per_op"])):
                    state = tiny_work(state)
                if state != int(row["result"]):
                    errors.append(f"processus {run_id}, échantillon {row['sample']} : résultat inexact")
                    break

    if errors:
        raise SystemExit("\n".join(errors))
    replayed = " et résultats rejoués" if args.replay else ""
    print(f"vérification : {len(plan)} processus complets{replayed}, OK")


if __name__ == "__main__":
    main()
