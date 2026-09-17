#!/usr/bin/env python3
"""Analyse statique du code machine des noyaux, indépendante de toute mesure.

Pour chaque binaire et chaque noyau : boucle présente (saut arrière), branchement
conditionnel à l'intérieur d'une boucle (saut conditionnel vers l'avant situé
entre la cible et la source d'un saut arrière), instructions conditionnelles sans
branchement (cmov, set, sbb/adc), registres vectoriels (xmm, ymm) et
multiplications. Extraits en syntaxe Intel dans reports/asm/.
"""

import argparse
import csv
import re
import subprocess
from pathlib import Path

KERNELS = ("chain_xor_mul", "split_xor_mul", "sum_one", "sum_four", "sum_twice",
           "sum_if", "filter_copy", "filter_copy_mask")
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
        if current is None:
            continue
        if not line.strip():
            current = None
            continue
        parts = line.strip().split("\t")
        if len(parts) >= 2:
            functions[current].append((int(parts[0].rstrip(":"), 16), parts[1].strip()))
    return functions


def describe(instructions):
    useful = [(a, i) for a, i in instructions if i.split()[0] not in PADDING]
    jumps = []
    for address, instruction in useful:
        mnemonic, _, operands = instruction.partition(" ")
        target = TARGET.match(operands.strip())
        if mnemonic.startswith("j") and target:
            jumps.append((address, int(target.group(1), 16), mnemonic != "jmp"))
    loops = [(target, address) for address, target, _ in jumps if target < address]
    in_loop_branches = sum(
        1 for address, target, conditional in jumps
        if conditional and target > address
        and any(start <= address < end for start, end in loops))
    mnemonics = [i.split()[0] for _, i in useful]
    return {
        "instructions": len(useful),
        "loops": len(loops),
        "branches_inside_loops": in_loop_branches,
        "conditional_moves": sum(m.startswith(("cmov", "set")) or m in ("sbb", "adc") for m in mnemonics),
        "uses_xmm": int(any(re.search(r"\bxmm\d+\b", i) for _, i in useful)),
        "uses_ymm": int(any(re.search(r"\bymm\d+\b", i) for _, i in useful)),
        "multiplications": sum(m in ("mul", "imul") or m.startswith("vpmul") or m == "pmuludq" for m in mnemonics),
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
        build = binary.name.removeprefix("bench-")
        functions = disassemble(binary)
        for kernel in KERNELS:
            instructions = functions[kernel]
            rows.append({"build": build, "kernel": kernel, **describe(instructions)})
            listing = "\n".join(f"{address:6x}:  {instruction}" for address, instruction in instructions)
            (excerpts / f"{build}-{kernel}.s").write_text(
                f"; {kernel}, {build}, syntaxe Intel (objdump -M intel)\n{listing}\n", encoding="utf-8")
    with (args.reports / "assembly.csv").open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"assembleur : {len(rows)} fonctions analysées, extraits dans {excerpts}")


if __name__ == "__main__":
    main()
