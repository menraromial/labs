#!/usr/bin/env python3
"""Vérifications indépendantes de la mesure.

1. Plan complet, épinglage respecté, aucune durée hors limite.
2. Exactitude : chaque bloc lu ou enregistrement relu a la somme attendue (harnais),
   et le nombre attendu est recalculé ici à partir du plan des mesures.
3. État du cache de pages, selon mincore : aucune page de notre fichier avant une
   lecture « à froid », toutes avant une lecture « à chaud ».
4. Comptes du noyau pour le processus (/proc/self/io) : nombre exact d'appels read
   et write ; aucun octet lu du stockage pour une lecture à chaud ; au moins les
   octets demandés pour une lecture à froid ou directe ; aucun octet compté pour tmpfs.
5. Latences par opération : leur somme égale la durée de l'échantillon.
6. Contenu du fichier lu : blocs tirés au hasard régénérés ici en Python, comparés
   octet à octet au fichier sur disque.

Les compteurs de toute la machine (disque, journal) ne sont pas vérifiés ici :
d'autres processus peuvent y contribuer. analyze.py les résume.
"""

import argparse
import csv
import random
from collections import defaultdict
from pathlib import Path

import numpy as np

PAGE = 4096
WORDS = PAGE // 8
SEQ_CHUNK = 128 * 1024
READS = {"seq_read_warm", "seq_read_cold", "seq_read_direct", "rand_read_warm", "rand_read_cold",
         "rand_read_cold_bis", "rand_read_direct", "rand_read_direct_double"}
WRITES = {"append_buffered", "append_fsync", "append_fdatasync", "tmpfs_append_fsync", "overwrite_fsync",
          "overwrite_fdatasync", "overwrite_fdatasync_bis", "overwrite_fdatasync_double", "overwrite_odsync",
          "overwrite_fdatasync_folio", "overwrite_odsync_folio"}
BATCHES = (1, 4, 16, 64, 256)
MEASURES_PER_ROUND = len(READS) + len(WRITES) + len(BATCHES) - 1


def expected_shape(label, param, ops_per_sample, file_pages):
    """(opérations, unités par opération) prévus par le plan des mesures."""
    if label.startswith("seq_read"):
        return file_pages * PAGE // SEQ_CHUNK, SEQ_CHUNK // PAGE
    if label == "append_fsync":
        return ops_per_sample // param, param
    if label.endswith("_double"):
        return ops_per_sample, 2
    return ops_per_sample, 1


def mix64(x):
    with np.errstate(over="ignore"):
        x = x + np.uint64(0x9E3779B97F4A7C15)
        x = (x ^ (x >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
        x = (x ^ (x >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
        return x ^ (x >> np.uint64(31))


def check_read_file(path, file_pages, samples=64):
    if not path.exists():
        return f"{path} absent : contenu non vérifié"
    if path.stat().st_size != file_pages * PAGE:
        return f"{path} : taille inattendue"
    blocks = [0, file_pages - 1] + random.Random(20260921).sample(range(file_pages), min(samples, file_pages))
    with path.open("rb") as source:
        for block in blocks:
            source.seek(block * PAGE)
            actual = np.frombuffer(source.read(PAGE), dtype="<u8")
            expected = mix64(np.uint64(block * WORDS) + np.arange(WORDS, dtype=np.uint64))
            if not np.array_equal(actual, expected):
                return f"{path} : bloc {block} différent du contenu régénéré"
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--scratch", type=Path, default=Path("build/scratch"))
    args = parser.parse_args()

    with (args.directory / "plan.csv").open(newline="", encoding="utf-8") as source:
        plan = list(csv.DictReader(source))
    errors, notes, samples_checked, ops_checked = [], [], 0, 0
    for planned in plan:
        run_id = int(planned["run_id"])
        base = args.directory / f"run-{run_id:03d}"
        paths = [Path(f"{base}.csv"), Path(f"{base}-ops.csv"), Path(f"{base}-meta.csv")]
        if not all(p.exists() for p in paths):
            errors.append(f"processus {run_id} : fichier absent")
            continue
        with paths[0].open(newline="", encoding="utf-8") as source:
            rows = list(csv.DictReader(source))
        with paths[2].open(newline="", encoding="utf-8") as source:
            meta = next(csv.DictReader(source))
        latency_sum, latency_count = defaultdict(int), defaultdict(int)
        with paths[1].open(newline="", encoding="utf-8") as source:
            for row in csv.DictReader(source):
                latency_sum[int(row["sample"])] += int(row["latency_ns"])
                latency_count[int(row["sample"])] += 1

        ops_per_sample, file_pages = int(planned["ops"]), int(planned["file_mib"]) * 256
        if len(rows) != MEASURES_PER_ROUND * int(planned["rounds"]):
            errors.append(f"processus {run_id} : {len(rows)} lignes inattendues")
        if meta["invalid_samples"] != "0" or meta["latency_over_limit"] != "0":
            errors.append(f"processus {run_id} : échantillons invalides signalés par le harnais")
        if any(r["cpu_before"] != planned["cpu"] or r["cpu_after"] != planned["cpu"] for r in rows):
            errors.append(f"processus {run_id} : épinglage non respecté")
        offsets = {int(r["read_syscalls"]) for r in rows if r["label"] in WRITES}
        if len(offsets) != 1:
            errors.append(f"processus {run_id} : décalage de lecture de /proc/self/io non constant {offsets}")
            continue
        offset = offsets.pop()
        for r in rows:
            label, param, sample = r["label"], int(r["param"]), int(r["sample"])
            where = f"processus {run_id}, échantillon {sample} ({label}, {param})"
            ops, units = expected_shape(label, param, ops_per_sample, file_pages)
            total = ops * units
            if (int(r["ops"]), int(r["units_per_op"])) != (ops, units) or int(r["file_pages"]) != file_pages:
                errors.append(f"{where} : forme de mesure inattendue")
                break
            if int(r["result"]) != total or int(r["expected"]) != total:
                errors.append(f"{where} : {r['result']} unités correctes sur {total}")
                break
            reads, writes = int(r["read_syscalls"]) - offset, int(r["write_syscalls"])
            read_bytes, write_bytes = int(r["read_bytes"]), int(r["write_bytes"])
            if label in READS:
                if (reads, writes) != (total if not label.startswith("seq") else ops, 0):
                    errors.append(f"{where} : appels read/write {reads, writes}")
                    break
                if label.endswith("_cold") or label.endswith("_cold_bis"):
                    if int(r["resident_before"]) != 0:
                        errors.append(f"{where} : {r['resident_before']} pages déjà en cache")
                        break
                    if read_bytes < total * PAGE:
                        errors.append(f"{where} : {read_bytes} octets lus du stockage, moins que demandé")
                        break
                elif label.endswith("_warm"):
                    if int(r["resident_before"]) != file_pages or read_bytes != 0:
                        errors.append(f"{where} : cache incomplet ou lecture du stockage ({read_bytes} octets)")
                        break
                elif read_bytes < total * PAGE:
                    errors.append(f"{where} : lecture directe de {read_bytes} octets seulement")
                    break
            else:
                if (reads, writes) != (0, total):
                    errors.append(f"{where} : appels read/write {reads, writes}")
                    break
                if label.startswith("tmpfs") and write_bytes != 0:
                    errors.append(f"{where} : {write_bytes} octets d'écriture comptés sur tmpfs")
                    break
            if not label.startswith("seq"):
                if latency_count[sample] != ops or latency_sum[sample] != int(r["elapsed_ns"]):
                    errors.append(f"{where} : latences par opération incohérentes")
                    break
                ops_checked += ops
            samples_checked += 1
        if int(meta["residency_retries"]) != 0:
            notes.append(f"processus {run_id} : {meta['residency_retries']} nouvelles demandes de retrait du cache")

    problem = check_read_file(args.scratch / f"read-{plan[0]['file_mib']}.dat", int(plan[0]["file_mib"]) * 256)
    if problem is not None:
        (errors if "absent" not in problem else notes).append(problem)
    for note in notes:
        print(f"note : {note}")
    if errors:
        raise SystemExit("\n".join(errors[:20]))
    print(f"vérification : {len(plan)} processus, {samples_checked} échantillons, {ops_checked} opérations ; "
          f"épinglage, résultats relus exacts, état du cache, appels et octets comptés par le noyau, "
          f"contenu du fichier lu régénéré : OK")


if __name__ == "__main__":
    main()
