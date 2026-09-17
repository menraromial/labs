#!/usr/bin/env python3
"""Vérifications indépendantes de la mesure.

1. Plan complet, épinglage respecté, fichier d'entrée identique à son empreinte.
2. Données : la somme des clés dérivées par chaque version égale celle recalculée ici.
3. Exactitude : chaque résultat égale la valeur recalculée ici en Python à partir du
   fichier d'entrée. Pour `dot`, les boucles strictes (contrôlées et idiomatiques en C,
   Rust et Go) doivent donner exactement le même flottant ; `math.sumprod` et `np.dot`,
   qui somment autrement, doivent en être à moins de 1e-12 en valeur relative.
4. Démarrage : toutes les commandes lancées se sont terminées avec le code 0.
"""

import argparse
import csv
import hashlib
import struct
from collections import Counter
from pathlib import Path

import numpy as np

K = 0x9E3779B97F4A7C15
MASK = (1 << 64) - 1
MEASURES = {"c-O2": 5, "c-O3": 5, "rust": 9, "go": 9, "python": 11}
STARTUP_LABELS = {"c-O2", "c-O3", "rust", "go", "python", "python-numpy"}
INEXACT = {("python", "dot", "idiomatic"), ("python", "dot", "numpy")}


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def expected_results(input_path, scale):
    n_hash = 1 << (20 - scale)
    n_dot, n_count = n_hash, 1 << (22 - scale)
    u = np.fromfile(input_path, dtype="<u8", count=max(n_count, 2 * n_dot))
    values = u[:n_hash].tolist()
    h = 0
    for x in values:
        h = ((h ^ x) * K) & MASK
    single = h
    for x in values:
        h = ((h ^ x) * K) & MASK
    a = ((u[:n_dot] >> np.uint64(11)).astype(np.float64) * 2.0**-53).tolist()
    b = ((u[n_dot:2 * n_dot] >> np.uint64(11)).astype(np.float64) * 2.0**-53).tolist()
    s = 0.0
    for x, y in zip(a, b):
        s += x * y
    keys = (((u[:n_count] >> np.uint64(48)) * ((u[:n_count] >> np.uint64(32)) & np.uint64(0xFFFF)))
            >> np.uint64(16)).astype(np.int64)
    counts = Counter(dict(enumerate(np.bincount(keys, minlength=1 << 16).tolist())))
    checksum = sum(c * (((k + 1) * K) & MASK) for k, c in counts.items() if c) & MASK
    return {"hash_single": single, "hash_double": h, "dot": s, "count": checksum,
            "keys_sum": int(keys.sum())}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--input", type=Path, default=Path("build/input.bin"))
    args = parser.parse_args()

    errors = []
    recorded = (args.directory / "input.sha256").read_text().split()[0]
    if hashlib.sha256(args.input.read_bytes()).hexdigest() != recorded:
        errors.append("fichier d'entrée différent de son empreinte")
    plan = read_csv(args.directory / "plan.csv")
    expected = {}
    samples = 0
    for planned in plan:
        run_id, build = int(planned["run_id"]), planned["build"]
        scale = int(planned["scale_log2"])
        if scale not in expected:
            expected[scale] = expected_results(args.input, scale)
        reference = expected[scale]
        base = args.directory / f"run-{run_id:03d}"
        try:
            rows, meta = read_csv(Path(f"{base}.csv")), read_csv(Path(f"{base}-meta.csv"))[0]
        except FileNotFoundError:
            errors.append(f"processus {run_id} : fichier absent")
            continue
        if len(rows) != MEASURES[build] * int(planned["rounds"]):
            errors.append(f"processus {run_id} ({build}) : {len(rows)} lignes inattendues")
        if int(meta["keys_sum"]) != reference["keys_sum"]:
            errors.append(f"processus {run_id} ({build}) : clés dérivées différentes")
        if build == "python" and (meta["jit"] != "False" or int(meta["gc_total"]) < 0):
            errors.append(f"processus {run_id} : JIT actif ou compte de collectes incohérent")
        for row in rows:
            where = f"processus {run_id} ({build}), {row['workload']} {row['variant']}"
            if row["cpu_before"] != planned["cpu"] or row["cpu_after"] != planned["cpu"]:
                errors.append(f"{where} : épinglage non respecté")
                break
            value = int(row["result"], 16)
            if row["workload"] == "hash_chain":
                good = value == reference["hash_double" if row["passes"] == "2" else "hash_single"]
            elif row["workload"] == "count":
                good = value == reference["count"]
            else:
                measured = struct.unpack("<d", struct.pack("<Q", value))[0]
                if (build, row["workload"], row["variant"]) in INEXACT:
                    good = abs(measured - reference["dot"]) <= 1e-12 * abs(reference["dot"])
                else:
                    good = measured == reference["dot"]
            if not good:
                errors.append(f"{where} : résultat inexact")
                break
            samples += 1
    startup = read_csv(args.directory / "startup.csv")
    reps = int((args.directory / "startup-reps.txt").read_text())
    if {r["label"] for r in startup} != STARTUP_LABELS or len(startup) != reps * len(STARTUP_LABELS):
        errors.append("mesure du démarrage incomplète")
    if any(r["status"] != "0" for r in startup):
        errors.append("une commande de démarrage a échoué")
    if errors:
        raise SystemExit("\n".join(errors[:20]))
    print(f"vérification : {len(plan)} processus, {samples} échantillons exacts, {len(startup)} démarrages, "
          f"épinglage, données et empreinte d'entrée : OK")


if __name__ == "__main__":
    main()
