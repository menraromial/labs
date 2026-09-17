#!/usr/bin/env python3
"""Vérifications indépendantes de la mesure.

1. Plan complet : chaque processus prévu a produit toutes ses lignes.
2. Épinglage respecté ; pages de 4 Kio effectivement utilisées (aucune page
   anonyme géante déclarée dans /proc/self/smaps_rollup).
3. Exactitude : chaque résultat égale la référence calculée par le harnais.
4. Avec ``--replay`` : les résultats sont recalculés en Python à partir de la
   graine, du départ et du sel de chaque échantillon.
"""

import argparse
import csv
from pathlib import Path

MASK = (1 << 64) - 1
GOLDEN = 0x9E3779B97F4A7C15
MEASURES = {"stride_1": ("stride", 1, 1), "stride_1_bis": ("stride", 1, 1),
            "stride_1_double": ("stride", 1, 2), "stride_17": ("stride", 17, 1),
            "stride_513": ("stride", 513, 1), "stride_4097": ("stride", 4097, 1),
            "random": ("random", 0, 1), "pair_same_line": ("pair", 3, 1),
            "pair_split_line": ("pair", 7, 1)}


def splitmix64(value):
    value = (value + GOLDEN) & MASK
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK
    return value ^ (value >> 31)


def mix(salt, j):
    x = (salt + j * GOLDEN) & MASK
    x ^= x >> 31
    x = (x * 0xBF58476D1CE4E5B9) & MASK
    return x ^ (x >> 29)


def replay(row, data):
    pattern, parameter, _ = MEASURES[row["label"]]
    n = int(row["bytes"]) // 8
    accesses, start, salt = int(row["accesses"]), int(row["start"]), int(row["salt"])
    total = 0
    if pattern == "stride":
        stride = parameter % n or 1
        for j in range(accesses):
            total += data[(start + j * stride) % n]
    elif pattern == "random":
        for j in range(accesses):
            total += data[(mix(salt, j) * n) >> 64]
    else:
        lines = n // 8
        for j in range(accesses):
            base = ((mix(salt, j) * (lines - 1)) >> 64) * 8 + parameter
            total += data[base] + data[base + 1]
    return total & MASK


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--replay", action="store_true")
    args = parser.parse_args()

    with (args.directory / "plan.csv").open(newline="", encoding="utf-8") as source:
        plan = list(csv.DictReader(source))
    errors, data_cache = [], {}
    for planned in plan:
        run_id = int(planned["run_id"])
        path = args.directory / f"run-{run_id:03d}.csv"
        meta_path = args.directory / f"run-{run_id:03d}-meta.csv"
        if not path.exists() or not meta_path.exists():
            errors.append(f"processus {run_id} : fichier absent")
            continue
        with path.open(newline="", encoding="utf-8") as source:
            rows = list(csv.DictReader(source))
        with meta_path.open(newline="", encoding="utf-8") as source:
            meta = next(csv.DictReader(source))
        sizes = 2 * (int(planned["max_log2"]) - int(planned["min_log2"])) + 1
        if len(rows) != sizes * len(MEASURES) * int(planned["rounds"]):
            errors.append(f"processus {run_id} : {len(rows)} lignes inattendues")
        if any(r["cpu_before"] != planned["cpu"] or r["cpu_after"] != planned["cpu"] for r in rows):
            errors.append(f"processus {run_id} : épinglage sur le CPU {planned['cpu']} non respecté")
        if meta["madvise_nohugepage"] != "1" or meta["anon_huge_pages_kb"] != "0":
            errors.append(f"processus {run_id} : pages géantes présentes ou conseil refusé")
        if any(r["result"] != r["expected"] for r in rows):
            errors.append(f"processus {run_id} : résultat différent de la référence")
        if args.replay:
            seed, top = int(planned["seed"]), 1 << int(planned["max_log2"])
            if (seed, top) not in data_cache:
                data_cache[(seed, top)] = [splitmix64(seed + i) for i in range(top // 8)]
            for row in rows:
                if replay(row, data_cache[(seed, top)]) != int(row["expected"]):
                    errors.append(f"processus {run_id} : référence non reproduite en Python ({row['label']})")
                    break
    if errors:
        raise SystemExit("\n".join(errors[:20]))
    replayed = ", résultats recalculés en Python" if args.replay else ""
    print(f"vérification : {len(plan)} processus complets, épinglés, en pages de 4 Kio, "
          f"résultats exacts{replayed}, OK")


if __name__ == "__main__":
    main()
