#!/usr/bin/env python3
"""Vérifications indépendantes de la mesure.

1. Plan complet : chaque processus prévu a produit toutes ses lignes, et le
   binaire déclare lui-même le jeu d'options attendu.
2. Épinglage respecté.
3. Exactitude : chaque résultat égale sa valeur attendue et chaque tampon de
   filtre a été vérifié par le harnais ; les valeurs attendues des mesures sans
   mélange sont identiques pour tous les binaires.
4. Avec ``--replay`` : les valeurs attendues des parties dépendance et petites
   tailles sont recalculées en Python.
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path

MASK = (1 << 64) - 1
MULTIPLIER = 0x9E3779B97F4A7C15
MEASURES_PER_ROUND = 6 + 3 * 9 + 20


def splitmix64(value):
    value = (value + 0x9E3779B97F4A7C15) & MASK
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK
    return value ^ (value >> 31)


def replay(label, n, seed):
    data = [splitmix64(seed + i) for i in range(n)]
    if label == "chain_xor_mul":
        value = 0
        for x in data:
            value = ((value ^ x) * MULTIPLIER) & MASK
        return value
    if label == "split_xor_mul":
        value = 0
        for x in data:
            value ^= (x * MULTIPLIER) & MASK
        return value
    total = sum(data) & MASK
    return (2 * total) & MASK if label == "sum_twice" else total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--replay", action="store_true")
    args = parser.parse_args()

    with (args.directory / "plan.csv").open(newline="", encoding="utf-8") as source:
        plan = list(csv.DictReader(source))
    errors, expected = [], defaultdict(set)
    cache = {}
    for planned in plan:
        run_id = int(planned["run_id"])
        path = args.directory / f"run-{run_id:03d}.csv"
        if not path.exists() or not (args.directory / f"run-{run_id:03d}-meta.csv").exists():
            errors.append(f"processus {run_id} : fichier absent")
            continue
        with path.open(newline="", encoding="utf-8") as source:
            rows = list(csv.DictReader(source))
        if len(rows) != MEASURES_PER_ROUND * int(planned["rounds"]):
            errors.append(f"processus {run_id} : {len(rows)} lignes inattendues")
        if any(row["build"] != planned["build"] for row in rows):
            errors.append(f"processus {run_id} : le binaire ne déclare pas {planned['build']}")
        if any(row["cpu_before"] != planned["cpu"] or row["cpu_after"] != planned["cpu"] for row in rows):
            errors.append(f"processus {run_id} : épinglage sur le CPU {planned['cpu']} non respecté")
        for row in rows:
            if row["result"] != row["expected"] or row["output_ok"] != "1":
                errors.append(f"processus {run_id} : résultat inexact ({row['label']}, {row['dataset']})")
                break
            expected[(row["label"], row["dataset"], row["n"], row["calls"])].add(row["expected"])
            if args.replay and row["part"] in ("dependency", "small"):
                key = (row["label"].removesuffix("_bis"), int(row["n"]), int(row["seed"]))
                if key not in cache:
                    cache[key] = replay(*key)
                if (cache[key] * int(row["calls"])) & MASK != int(row["expected"]):
                    errors.append(f"processus {run_id} : valeur attendue non reproduite en Python ({row['label']})")
                    break
    divergent = [k for k, v in expected.items() if len(v) != 1]
    if divergent:
        errors.append(f"{len(divergent)} mesures avec des valeurs attendues différentes selon le binaire")
    if errors:
        raise SystemExit("\n".join(errors[:20]))
    replayed = ", valeurs attendues recalculées en Python" if args.replay else ""
    print(f"vérification : {len(plan)} processus complets, résultats et tampons exacts, "
          f"identiques pour tous les binaires{replayed}, OK")


if __name__ == "__main__":
    main()
