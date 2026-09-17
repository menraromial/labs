#!/usr/bin/env python3
"""Vérifications indépendantes de la mesure.

1. Plan complet et épinglage respecté.
2. Exactitude : chaque résultat égale la valeur attendue, recalculée ici en Python
   à partir du nombre d'appels et de la taille des blocs.
3. Nombre d'appels système, compté par le noyau (/proc/self/io) : exactement le
   nombre attendu pour chaque mesure de lecture ou d'écriture, après retrait du
   décalage constant dû à la lecture de /proc/self/io elle-même (mesuré sur les
   mesures qui ne lisent rien).
"""

import argparse
import csv
from pathlib import Path

RECORD = 16
MEASURES_PER_ROUND = 7 + 2 * 11 + 4


def ceil_div(a, b):
    return -(-a // b)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()

    with (args.directory / "plan.csv").open(newline="", encoding="utf-8") as source:
        plan = list(csv.DictReader(source))
    errors = []
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
        if len(rows) != MEASURES_PER_ROUND * int(planned["rounds"]):
            errors.append(f"processus {run_id} : {len(rows)} lignes inattendues")
        if any(r["cpu_before"] != planned["cpu"] or r["cpu_after"] != planned["cpu"] for r in rows):
            errors.append(f"processus {run_id} : épinglage non respecté")
        offsets = {int(r["read_syscalls"]) for r in rows if r["label"] == "function_call"}
        if len(offsets) != 1:
            errors.append(f"processus {run_id} : décalage de lecture non constant {offsets}")
            continue
        offset = offsets.pop()
        buffer = int(meta["stdio_default_buffer"])
        for r in rows:
            label, calls, chunk = r["label"], int(r["calls"]), int(r["chunk"])
            reads, writes = int(r["read_syscalls"]) - offset, int(r["write_syscalls"])
            expected_io = (0, 0)
            if label == "write_dev_null":
                expected_value, expected_io = chunk * calls, (0, calls)
            elif label == "read_dev_zero":
                expected_value, expected_io = chunk * calls, (calls, 0)
            elif label == "records_write_each":
                expected_value, expected_io = RECORD * calls, (0, calls)
            elif label == "records_stdio_default":
                expected_value, expected_io = RECORD * calls, (0, ceil_div(RECORD * calls, buffer))
            elif label == "records_stdio_64k":
                expected_value, expected_io = RECORD * calls, (0, ceil_div(RECORD * calls, 65536))
            elif label == "records_manual_4k":
                expected_value, expected_io = RECORD * calls, (0, ceil_div(RECORD * calls, 4096))
            elif label == "function_call":
                expected_value = calls * (calls + 1) // 2
            elif label in ("vdso_clock_gettime", "syscall_clock_gettime", "syscall_enosys"):
                expected_value = calls
            else:
                expected_value = None   # getppid : dépend du processus parent, vérifié par le harnais
            if expected_value is not None and int(r["result"]) != expected_value:
                errors.append(f"processus {run_id} : résultat inexact ({label}, bloc {chunk})")
                break
            if r["result"] != r["expected"]:
                errors.append(f"processus {run_id} : résultat différent de la référence du harnais ({label})")
                break
            if (reads, writes) != expected_io:
                errors.append(f"processus {run_id} : appels système {reads, writes} au lieu de {expected_io} ({label}, bloc {chunk})")
                break
    if errors:
        raise SystemExit("\n".join(errors[:20]))
    print(f"vérification : {len(plan)} processus complets, épinglés, résultats exacts, "
          f"nombres d'appels read et write conformes aux comptes du noyau, OK")


if __name__ == "__main__":
    main()
