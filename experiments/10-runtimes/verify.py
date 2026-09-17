#!/usr/bin/env python3
"""Vérifications indépendantes de la mesure (E2).

1. Plan complet ; CPU autorisés de chaque processus égaux à ceux du plan (lus par le
   processus lui-même dans /proc/self/status) ; empreinte du fichier d'entrée.
2. Échauffement : chaque résultat égale la chaîne de hachage et le produit scalaire strict
   recalculés ici en Python ; l'état du JIT déclaré par le processus correspond à son mode.
3. Allocation : nombre d'opérations et somme de contrôle de l'anneau final recalculés ici.
4. Démarrage : chaque commande terminée avec le code 0 ; traces de décomposition présentes.
"""

import argparse
import csv
import hashlib
import struct
from pathlib import Path

import numpy as np

K = 0x9E3779B97F4A7C15
MASK = (1 << 64) - 1
EXPECTED_JIT = {"c": "none", "java": "enabled", "java-xint": "disabled", "java-2cpu": "enabled",
                "node": "enabled", "node-jitless": "disabled", "node-2cpu": "enabled",
                "python": "disabled", "python-jit": "enabled"}
STARTUP_LABELS = {"c-dynamic", "c-static", "rust", "go", "python", "python-no-site", "python-isolated",
                  "python-numpy", "node", "node-jitless", "java", "java-no-cds"}


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def warm_expected(input_path, n):
    u = np.fromfile(input_path, dtype="<u8", count=2 * n)
    h = 0
    for x in u[:n].tolist():
        h = ((h ^ x) * K) & MASK
    a = ((u[:n] >> np.uint64(11)).astype(np.float64) * 2.0**-53).tolist()
    b = ((u[n:] >> np.uint64(11)).astype(np.float64) * 2.0**-53).tolist()
    s = 0.0
    for x, y in zip(a, b):
        s += x * y
    return {"hash_chain": h, "dot": struct.unpack("<Q", struct.pack("<d", s))[0]}


def churn_checksum(live, operations):
    # anneau final : objets d'indices operations+live-live ... ; clé i, a = 2i+1, b = 3i+2
    total = live + operations
    first = total - live
    indices_sum = (first + total - 1) * live // 2
    return (6 * indices_sum + 3 * live) & MASK


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--input", type=Path, default=Path("build/input.bin"))
    args = parser.parse_args()
    errors, warm_rows, churn_batches = [], 0, 0
    recorded = (args.directory / "input.sha256").read_text().split()[0]
    if hashlib.sha256(args.input.read_bytes()).hexdigest() != recorded:
        errors.append("fichier d'entrée différent de son empreinte")
    expected = {}
    for planned in read_csv(args.directory / "plan.csv"):
        run_id, part, mode = int(planned["run_id"]), planned["part"], planned["mode"]
        base = args.directory / f"{part}-{run_id:03d}"
        try:
            rows, meta = read_csv(Path(f"{base}.csv")), read_csv(Path(f"{base}-meta.csv"))[0]
        except FileNotFoundError:
            errors.append(f"processus {run_id} ({part}, {mode}) : fichier absent")
            continue
        where = f"processus {run_id} ({part}, {mode})"
        if meta["cpus_allowed"] != planned["cpus"]:
            errors.append(f"{where} : CPU autorisés {meta['cpus_allowed']} au lieu de {planned['cpus']}")
        if part == "warm":
            n = 1 << int(planned["n_log2"])
            if n not in expected:
                expected[n] = warm_expected(args.input, n)
            if len(rows) != 2 * int(planned["steps"]):
                errors.append(f"{where} : {len(rows)} lignes")
            if meta["jit"] != EXPECTED_JIT[mode]:
                errors.append(f"{where} : JIT {meta['jit']} au lieu de {EXPECTED_JIT[mode]}")
            if any(int(r["result"], 16) != expected[n][r["workload"]] for r in rows):
                errors.append(f"{where} : résultat inexact")
            if mode == "c" and any(r["cpu"] != "11" for r in rows):
                errors.append(f"{where} : échantillon hors du CPU 11")
            warm_rows += len(rows)
        else:
            live = 1 << int(planned["live_log2"])
            operations = int(planned["batches"]) << int(planned["batch_log2"])
            if len(rows) != int(planned["batches"]) or int(meta["operations"]) != operations:
                errors.append(f"{where} : plan incomplet")
            if int(meta["checksum"]) != churn_checksum(live, operations):
                errors.append(f"{where} : somme de contrôle inexacte")
            churn_batches += len(rows)
    startup = read_csv(args.directory / "startup.csv")
    reps, decomposition_reps = map(int, (args.directory / "startup-reps.txt").read_text().split())
    if {r["label"] for r in startup} != STARTUP_LABELS or len(startup) != reps * len(STARTUP_LABELS):
        errors.append("mesure du démarrage incomplète")
    if any(r["status"] != "0" for r in startup):
        errors.append("une commande de démarrage a échoué")
    traces = list((args.directory / "decomposition").glob("*.txt"))
    if len(traces) != 4 * decomposition_reps or any(p.stat().st_size == 0 for p in traces):
        errors.append("traces de décomposition incomplètes")
    if errors:
        raise SystemExit("\n".join(errors[:20]))
    print(f"vérification : {warm_rows} pas d'échauffement exacts, {churn_batches} lots d'allocation, "
          f"{len(startup)} démarrages, {len(traces)} traces ; CPU autorisés, JIT, sommes de contrôle : OK")


if __name__ == "__main__":
    main()
