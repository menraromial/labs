#!/usr/bin/env python3
"""Analyse statique du code machine des noyaux, indépendante de toute mesure.

Pour chaque binaire et chaque noyau : nombre d'instructions utiles, présence
d'une boucle (saut vers une adresse antérieure de la même fonction), accès
mémoire et emploi de registres vectoriels. Les extraits sont conservés dans
reports/asm/ en syntaxe Intel.
"""

import argparse
import csv
import re
import subprocess
from pathlib import Path

KERNELS = ("sum_array", "sum_array_twice", "sum_discarded", "sum_indices")
JUMP = re.compile(r"^j[a-z]+$")
TARGET = re.compile(r"^([0-9a-f]+) <")
PADDING = {"nop", "xchg", "data16", "int3", "endbr64"}


def disassemble(binary):
    text = subprocess.run(["objdump", "-d", "--no-show-raw-insn", "-M", "intel", str(binary)],
                          check=True, capture_output=True, text=True).stdout
    functions, current = {}, None
    for line in text.splitlines():
        header = re.match(r"^[0-9a-f]+ <([A-Za-z0-9_]+)>:$", line)
        if header:
            current = header.group(1) if header.group(1) in KERNELS else None
            if current:
                functions[current] = []
            continue
        if current is None or not line.strip():
            if not line.strip():
                current = None
            continue
        parts = line.strip().split("\t")
        if len(parts) < 2:
            continue
        address = int(parts[0].rstrip(":"), 16)
        instruction = parts[1].strip()
        functions[current].append((address, instruction))
    return functions


def describe(instructions):
    useful = [(a, i) for a, i in instructions if i.split()[0] not in PADDING]
    backward = 0
    for address, instruction in useful:
        mnemonic, _, operands = instruction.partition(" ")
        target = TARGET.match(operands.strip())
        if JUMP.match(mnemonic) and target and int(target.group(1), 16) < address:
            backward += 1
    return {
        "instructions": len(useful),
        "backward_jumps": backward,
        "has_loop": int(backward > 0),
        "memory_operands": sum("PTR [" in i for _, i in useful),
        "uses_vector_registers": int(any(re.search(r"\b[xyz]mm\d+\b", i) for _, i in useful)),
        "multiplications": sum(i.split()[0] in ("mul", "imul") for _, i in useful),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("binaries", nargs="+", type=Path)
    parser.add_argument("--reports", type=Path, required=True)
    args = parser.parse_args()

    excerpts = args.reports / "asm"
    excerpts.mkdir(parents=True, exist_ok=True)
    rows = []
    for binary in args.binaries:
        compiler, level = binary.name.removeprefix("bench-").split("-")
        functions = disassemble(binary)
        for kernel in KERNELS:
            instructions = functions[kernel]
            rows.append({"compiler": compiler, "level": level, "kernel": kernel,
                         **describe(instructions)})
            listing = "\n".join(f"{address:6x}:  {instruction}" for address, instruction in instructions)
            (excerpts / f"{compiler}-{level}-{kernel}.s").write_text(
                f"; {kernel}, {compiler} -{level}, syntaxe Intel (objdump -M intel)\n{listing}\n",
                encoding="utf-8")
    with (args.reports / "assembly.csv").open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"assembleur : {len(rows)} fonctions analysées, extraits dans {excerpts}")


if __name__ == "__main__":
    main()
