#!/usr/bin/env python3
"""Vérifications indépendantes de la mesure.

1. Plan complet : chaque processus prévu a produit toutes ses lignes.
2. Épinglage respecté ; pages de 4 Kio sans aucune page géante pour le mode 4k.
   Pour le mode 2m, la part de pages géantes obtenue est rapportée (le noyau peut
   en refuser une partie) et doit dépasser 50 % pour que le processus soit valide.
3. Exactitude : chaque résultat égale la référence calculée par le harnais.
4. Avec ``--replay`` : cycles de Sattolo et parcours recalculés en Python.
"""

import argparse
import csv
from pathlib import Path

MASK = (1 << 64) - 1
GOLDEN = 0x9E3779B97F4A7C15
MIN_HUGE_SHARE = 0.5


class XorShift:
    def __init__(self, state):
        self.state = state & MASK

    def next(self):
        s = self.state
        s ^= s >> 12
        s ^= (s << 25) & MASK
        s ^= s >> 27
        self.state = s
        return (s * 2685821657736338717) & MASK


def sattolo(n, seed):
    rng, values = XorShift(seed), list(range(n))
    for i in range(n - 1, 0, -1):
        j = rng.next() % i
        values[i], values[j] = values[j], values[i]
    return values


def mix(salt, j):
    x = (salt + j * GOLDEN) & MASK
    x ^= x >> 31
    x = (x * 0xBF58476D1CE4E5B9) & MASK
    return x ^ (x >> 29)


def replay(row, cycle):
    n, steps, start = int(row["bytes"]) // 8, int(row["accesses"]), int(row["start"])
    label = row["label"]
    if label.startswith("chase"):
        nxt = cycle if label.startswith("chase_random") else [(i + 1) % n for i in range(n)]
        total, index = 0, start
        for _ in range(steps):
            total += index
            index = nxt[index]
        return total & MASK
    salt = int(row["salt"])
    return sum(cycle[(mix(salt, j) * n) >> 64] for j in range(steps)) & MASK


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--replay", action="store_true")
    args = parser.parse_args()

    with (args.directory / "plan.csv").open(newline="", encoding="utf-8") as source:
        plan = list(csv.DictReader(source))
    errors, shares, cycles = [], [], {}
    for planned in plan:
        run_id = int(planned["run_id"])
        path, meta_path = args.directory / f"run-{run_id:03d}.csv", args.directory / f"run-{run_id:03d}-meta.csv"
        if not path.exists() or not meta_path.exists():
            errors.append(f"processus {run_id} : fichier absent")
            continue
        with path.open(newline="", encoding="utf-8") as source:
            rows = list(csv.DictReader(source))
        with meta_path.open(newline="", encoding="utf-8") as source:
            meta = next(csv.DictReader(source))
        sizes = int(planned["max_log2"]) - int(planned["min_log2"]) + 1
        if len(rows) != (5 * sizes + 2) * int(planned["rounds"]):
            errors.append(f"processus {run_id} : {len(rows)} lignes inattendues")
        if any(r["cpu_before"] != planned["cpu"] or r["cpu_after"] != planned["cpu"] for r in rows):
            errors.append(f"processus {run_id} : épinglage non respecté")
        if any(r["result"] != r["expected"] for r in rows):
            errors.append(f"processus {run_id} : résultat différent de la référence")
        share = float(meta["huge_share"])
        if planned["pages"] == "4k" and meta["anon_huge_pages_kb"] != "0":
            errors.append(f"processus {run_id} : pages géantes présentes en mode 4k")
        if planned["pages"] == "2m":
            shares.append(share)
            if share < MIN_HUGE_SHARE:
                errors.append(f"processus {run_id} : seulement {share:.0%} de pages géantes")
        if args.replay:
            seed = int(planned["seed"])
            for row in rows:
                if row["label"] == "page_fault_touch":
                    continue
                size_index = (int(row["bytes"]).bit_length() - 1) - int(planned["min_log2"])
                key = (int(row["bytes"]), seed + size_index)
                if key not in cycles:
                    cycles[key] = sattolo(int(row["bytes"]) // 8, seed + size_index)
                if replay(row, cycles[key]) != int(row["expected"]):
                    errors.append(f"processus {run_id} : référence non reproduite en Python ({row['label']})")
                    break
    if errors:
        raise SystemExit("\n".join(errors[:20]))
    share_text = f", pages géantes obtenues {min(shares):.0%} à {max(shares):.0%}" if shares else ""
    replayed = ", résultats recalculés en Python" if args.replay else ""
    print(f"vérification : {len(plan)} processus complets, épinglés, résultats exacts{share_text}{replayed}, OK")


if __name__ == "__main__":
    main()
