#!/usr/bin/env python3
"""Analyse statique : code machine des boucles mesurées en C, Rust et Go.

Pour chaque fonction : nombre d'instructions, appels (dont vérifications de bornes qui
paniquent), registres vectoriels, multiplications et sauts arrière (boucles). Les extraits
sont écrits dans reports/asm/, le résumé dans reports/assembly.csv.
"""

import argparse
import csv
import re
import subprocess
from pathlib import Path

FUNCTIONS = {
    "c-O2": ("build/bench-c-O2", {"hash_chain": "hash_chain", "dot": "dot", "count_table": "count_table"}),
    "c-O3": ("build/bench-c-O3", {"hash_chain": "hash_chain", "dot": "dot", "count_table": "count_table"}),
    "rust": ("build/bench-rust", {"hash_chain": "bench::hash_chain", "hash_chain_iter": "bench::hash_chain_iter",
                                  "dot": "bench::dot", "dot_iter": "bench::dot_iter",
                                  "count_table": "bench::count_table", "count_hashmap": "bench::count_hashmap"}),
    "go": ("build/bench-go", {"hash_chain": "main.hashChain", "hash_chain_iter": "main.hashChainRange",
                              "dot": "main.dot", "dot_iter": "main.dotRange",
                              "count_table": "main.countTable", "count_hashmap": "main.countMap"}),
}
PANIC = re.compile(r"panic_bounds_check|panicIndex|panicBounds|core::panicking")


def disassemble(binary):
    text = subprocess.run(["objdump", "-d", "-C", "--no-show-raw-insn", "-M", "intel", binary],
                          capture_output=True, text=True, check=True).stdout
    functions, name, body = {}, None, []
    for line in text.splitlines():
        header = re.match(r"^[0-9a-f]+ <(.+)>:$", line)
        if header:
            if name:
                functions[name] = body
            name, body = header.group(1), []
        elif name and line.strip():
            body.append(line)
    if name:
        functions[name] = body
    return functions


def summarize(body):
    addresses, calls, backward = [], [], 0
    for line in body:
        match = re.match(r"^\s*([0-9a-f]+):\s+(\S+)\s*(.*)$", line)
        if not match:
            continue
        address, mnemonic, operands = int(match.group(1), 16), match.group(2), match.group(3)
        addresses.append((address, mnemonic, operands))
    start = addresses[0][0] if addresses else 0
    for address, mnemonic, operands in addresses:
        if mnemonic.startswith("call"):
            calls.append(operands)
        if mnemonic.startswith("j"):
            target = re.match(r"([0-9a-f]+)", operands)
            if target and start <= int(target.group(1), 16) < address:
                backward += 1
    # Vérification de bornes : saut conditionnel vers le bloc froid final qui appelle une panique
    # (appel direct nommé chez Go, appel indirect par la GOT chez Rust).
    panic_blocks = [a for a, m, o in addresses if m.startswith("call") and (PANIC.search(o) or "rip+" in o)]
    first_panic = min(panic_blocks) if panic_blocks else None
    checked = 0
    for address, mnemonic, operands in addresses:
        target = re.match(r"([0-9a-f]+)", operands)
        if first_panic and mnemonic.startswith("j") and mnemonic != "jmp" and target:
            destination = int(target.group(1), 16)
            checked += destination >= first_panic - 16 and destination > address
    joined = " ".join(f"{m} {o}" for _, m, o in addresses)
    return {
        "instructions": len(addresses),
        "backward_jumps": backward,
        "calls": len(calls),
        "bounds_checks": checked,
        "simd": "ymm" if "ymm" in joined else ("xmm" if re.search(r"xmm|pmul|paddq", joined) else "non"),
        "packed_float_ops": len(re.findall(r"\b(mulpd|addpd)\b", joined)),
        "scalar_float_ops": len(re.findall(r"\b(mulsd|addsd)\b", joined)),
        "integer_mul": len(re.findall(r"\b(imul|mul)\b", joined)),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports", type=Path, default=Path("reports"))
    args = parser.parse_args()
    (args.reports / "asm").mkdir(parents=True, exist_ok=True)
    rows = []
    for build, (binary, wanted) in FUNCTIONS.items():
        functions = disassemble(binary)
        for label, symbol in wanted.items():
            body = functions.get(symbol)
            if body is None:
                rows.append({"build": build, "function": label, "symbol": symbol, "instructions": "absent"})
                continue
            (args.reports / "asm" / f"{build}-{label}.txt").write_text("\n".join(body) + "\n", encoding="utf-8")
            rows.append({"build": build, "function": label, "symbol": symbol, **summarize(body)})
    with (args.reports / "assembly.csv").open("w", newline="", encoding="utf-8") as target:
        fields = list(dict.fromkeys(k for r in rows for k in r))
        writer = csv.DictWriter(target, fieldnames=fields, restval="", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(",".join(str(row.get(f, "")) for f in fields))


if __name__ == "__main__":
    main()
