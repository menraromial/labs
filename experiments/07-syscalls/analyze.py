#!/usr/bin/env python3
"""Résumés et figures du projet D1.

Règles fixées avant la campagne (README, section 7) : unité statistique le
processus ; médiane par processus sur les tours hors échauffement ; médiane et
bootstrap percentile à 95 % entre processus ; rapports par processus ; modèle
S + b × bloc par moindres carrés relatifs sur les médianes ; part du temps
système sur les sommes des tours mesurés.
"""

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))
import figstyle  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.ticker import NullLocator  # noqa: E402

BOOTSTRAP_SAMPLES = 10_000
BOOTSTRAP_SEED = 20260920
CORES = ("P", "E", "LP-E")
CORE_LABELS = {"P": "Cœur P", "E": "Cœur E", "LP-E": "Cœur LP-E"}
CORE_COLOR = {"P": figstyle.PALETTE[0], "E": figstyle.PALETTE[1], "LP-E": figstyle.PALETTE[2]}
CORE_MARKER = {"P": "o", "E": "s", "LP-E": "^"}
ENTRY = ("function_call", "vdso_clock_gettime", "syscall_clock_gettime", "syscall_enosys", "syscall_getppid")
ENTRY_LABELS = {"function_call": "Appel de\nfonction", "vdso_clock_gettime": "clock_gettime\npar le vDSO",
                "syscall_clock_gettime": "clock_gettime\nappel système", "syscall_enosys": "Appel\ninexistant",
                "syscall_getppid": "getppid"}
RECORDS = ("records_write_each", "records_stdio_default", "records_stdio_64k", "records_manual_4k")
RECORD_LABELS = {"records_write_each": "write par\nenregistrement", "records_stdio_default": "fwrite,\ntampon 4 Kio",
                 "records_stdio_64k": "fwrite,\ntampon 64 Kio", "records_manual_4k": "Tampon manuel\nde 4 Kio"}
DEVICES = {"write_dev_null": "write sur /dev/null", "read_dev_zero": "read sur /dev/zero"}
DEVICE_STYLE = {"write_dev_null": "--", "read_dev_zero": "-"}


def fmt(value, digits=4):
    return f"{value:.{digits}f}" if value is not None and np.isfinite(value) else ""


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as target:
        fields = list(dict.fromkeys(key for row in rows for key in row))
        writer = csv.DictWriter(target, fieldnames=fields, restval="", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def bootstrap_median(values):
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    indices = rng.integers(0, values.size, size=(BOOTSTRAP_SAMPLES, values.size))
    low, high = np.percentile(np.median(values[indices], axis=1), [2.5, 97.5])
    return float(np.median(values)), float(low), float(high)


def size_label(size):
    for unit, scale in (("Mio", 1 << 20), ("Kio", 1 << 10)):
        if size >= scale:
            return f"{figstyle.french_number(size / scale)} {unit}"
    return f"{size} o"


# ---------------------------------------------------------------- lecture

def load(directory):
    processes = []
    for planned in read_csv(directory / "plan.csv"):
        run_id = int(planned["run_id"])
        cost, user, system = defaultdict(list), defaultdict(int), defaultdict(int)
        for row in read_csv(directory / f"run-{run_id:03d}.csv"):
            if row["phase"] != "measure":
                continue
            key = (row["label"], int(row["chunk"]))
            calls = int(row["calls"])
            per = 2 * calls if row["label"] == "syscall_getppid_double" else calls
            cost[key].append(int(row["elapsed_ns"]) / per)
            user[key] += int(row["user_us"])
            system[key] += int(row["system_us"])
        share = {k: system[k] / (user[k] + system[k]) if user[k] + system[k] > 0 else float("nan") for k in cost}
        processes.append({"core": planned["core"], "cost": {k: float(np.median(v)) for k, v in cost.items()},
                          "share": share, "meta": read_csv(directory / f"run-{run_id:03d}-meta.csv")[0]})
    return processes


def cost_of(process, label, chunk=0):
    return process["cost"][(label, chunk)]


# ---------------------------------------------------------------- analyses

def summary_rows(groups):
    rows, table = [], {}
    for core, selected in groups.items():
        for key in sorted(selected[0]["cost"]):
            values = [p["cost"][key] for p in selected]
            shares = [p["share"][key] for p in selected if np.isfinite(p["share"][key])]
            center, low, high = bootstrap_median(values)
            table[(core,) + key] = (values, center, low, high)
            rows.append({"core": core, "label": key[0], "chunk": key[1], "processes": len(values),
                         "median_ns_per_call": fmt(center, 3), "ci95_low": fmt(low, 3), "ci95_high": fmt(high, 3),
                         "median_system_share": fmt(float(np.median(shares)), 3) if shares else ""})
    return rows, table


def ratio_rows(groups):
    pairs = (("syscall_clock/vdso_clock", "syscall_clock_gettime", "vdso_clock_gettime"),
             ("enosys/getppid", "syscall_enosys", "syscall_getppid"),
             ("getppid/function", "syscall_getppid", "function_call"),
             ("aa_getppid_bis/getppid", "syscall_getppid_bis", "syscall_getppid"),
             ("positive_double/getppid", "syscall_getppid_double", "syscall_getppid"),
             ("records_write_each/stdio_default", "records_write_each", "records_stdio_default"),
             ("records_stdio_64k/stdio_default", "records_stdio_64k", "records_stdio_default"),
             ("records_manual_4k/stdio_default", "records_manual_4k", "records_stdio_default"))
    rows = []
    for core, selected in groups.items():
        for name, top, bottom in pairs:
            chunk_top = 16 if top.startswith("records") else 0
            chunk_bottom = 16 if bottom.startswith("records") else 0
            factor = 2 if top == "syscall_getppid_double" else 1   # durée d'une itération à deux appels
            values = [factor * p["cost"][(top, chunk_top)] / p["cost"][(bottom, chunk_bottom)] for p in selected]
            center, low, high = bootstrap_median(values)
            rows.append({"core": core, "ratio": name, "median": fmt(center, 3), "ci95_low": fmt(low, 3),
                         "ci95_high": fmt(high, 3), "min": fmt(min(values), 3), "max": fmt(max(values), 3)})
        write_16 = [p["cost"][("records_write_each", 16)] / p["cost"][("write_dev_null", 16)] for p in selected]
        center, low, high = bootstrap_median(write_16)
        rows.append({"core": core, "ratio": "records_write_each/write_dev_null_16", "median": fmt(center, 3),
                     "ci95_low": fmt(low, 3), "ci95_high": fmt(high, 3), "min": fmt(min(write_16), 3),
                     "max": fmt(max(write_16), 3)})
    for core in groups:
        if core == "P":
            continue
        for label in ("syscall_getppid", "syscall_enosys", "syscall_clock_gettime", "function_call"):
            top = [p["cost"][(label, 0)] for p in groups[core]]
            bottom = [p["cost"][(label, 0)] for p in groups["P"]]
            rows.append({"core": core, "ratio": f"{label} {core}/P",
                         "median": fmt(float(np.median(top) / np.median(bottom)), 3)})
    return rows


def model_rows(table, chunks):
    rows, fits = [], {}
    for core in CORES:
        for device in DEVICES:
            if (core, device, chunks[0]) not in table:
                continue
            y = np.array([table[(core, device, c)][1] for c in chunks])
            x = np.asarray(chunks, dtype=float)
            design = np.column_stack([1 / y, x / y])      # S / y + b x / y = 1
            (s, b), *_ = np.linalg.lstsq(design, np.ones_like(y), rcond=None)
            fits[(core, device)] = (s, b)
            rows.append({"core": core, "device": device, "S_ns_per_call": fmt(s, 2), "b_ns_per_byte": fmt(b, 6),
                         "crossover_bytes": fmt(s / b, 0) if b > 0 else "",
                         "per_call_1B_over_1MiB": fmt(y[0] / y[-1], 4),
                         "throughput_1MiB_gib_per_s": fmt(chunks[-1] / y[-1] * 1e9 / (1 << 30), 2)})
    return rows, fits


# ---------------------------------------------------------------- figures

def categorical(axis, labels):
    axis.set_xticks(range(len(labels)), labels)
    axis.tick_params(axis="x", length=0)
    axis.grid(axis="x", visible=False)
    axis.set_xlim(-0.6, len(labels) - 0.4)


def readable_log_axis(axis, *groups, pad=1.3, top_pad=None):
    data = np.concatenate([np.asarray(g, dtype=float).ravel() for g in groups])
    data = data[np.isfinite(data) & (data > 0)]
    low, high = data.min() / pad, data.max() * (top_pad or pad)
    multipliers = (1, 2, 3, 5) if high / low < 10 else (1, 2, 5)
    ticks = [m * 10.0 ** e for e in range(-6, 12) for m in multipliers if low <= m * 10.0 ** e <= high]
    if len(ticks) > 8:
        ticks = [t for t in ticks if np.isclose(t / 10 ** np.floor(np.log10(t)), 1)]
    axis.set_yscale("log")
    axis.set_ylim(low, high)
    figstyle.fixed_ticks(axis, "y", ticks)


def category_panel(axis, table, labels, names, chunk, ylabel, letter, title):
    everything = []
    for x, label in enumerate(labels):
        for offset, core in zip((-0.24, 0.0, 0.24), CORES):
            key = (core, label, chunk)
            if key not in table:
                continue
            values, center, low, high = table[key]
            everything.extend(values)
            figstyle.strip(axis, x + offset - 0.04, values, width=0.035, seed=x * 3 + len(core),
                           color=CORE_COLOR[core], marker=CORE_MARKER[core], s=8,
                           label=CORE_LABELS[core] if x == 0 else None)
            figstyle.interval(axis, x + offset + 0.06, center, low, high, markersize=2.4, capsize=1.3,
                              label="Médiane, IC 95 %" if x == 0 and core == "P" else None)
    categorical(axis, [names[l] for l in labels])
    readable_log_axis(axis, everything, pad=1.8)
    axis.set_ylabel(ylabel)
    axis.legend()
    figstyle.panel_title(axis, letter, title)


def plot_entry(table, path):
    figure, (entry, records) = figstyle.subplots(1, 2, height=2.6)
    category_panel(entry, table, ENTRY, ENTRY_LABELS, 0, "Coût par appel (ns)", "a", "Entrer dans le noyau")
    category_panel(records, table, RECORDS, RECORD_LABELS, 16, "Coût par enregistrement (ns)", "b",
                   "Écrire 2^20 enregistrements de 16 octets".replace("2^20", "$2^{20}$"))
    figstyle.save(figure, path)


def plot_batching(table, fits, chunks, path):
    # La part du temps système n'est pas tracée : getrusage répartit le temps exact du
    # processus selon des relevés au tick cumulés depuis son démarrage (README, 10.4).
    figure, (null_axis, zero_axis, byte_axis) = figstyle.subplots(1, 3, height=2.5)
    x = np.asarray(chunks, dtype=float)
    dense = np.geomspace(x[0], x[-1], 200)
    ticks = [c for c in chunks if int(np.log2(c)) % 4 == 0]
    for axis, device, letter, title in ((null_axis, "write_dev_null", "a", "write sur /dev/null"),
                                        (zero_axis, "read_dev_zero", "b", "read sur /dev/zero")):
        values = []
        for core in CORES:
            if (core, device, chunks[0]) not in table:
                continue
            y = np.array([table[(core, device, c)][1] for c in chunks])
            low = np.array([table[(core, device, c)][2] for c in chunks])
            high = np.array([table[(core, device, c)][3] for c in chunks])
            values.extend([low, high])
            axis.fill_between(x, low, high, color=CORE_COLOR[core], alpha=0.18, linewidth=0)
            axis.plot(x, y, color=CORE_COLOR[core], marker=CORE_MARKER[core], markersize=2.4,
                      label=CORE_LABELS[core])
        for index, core in enumerate(c for c in CORES if (c, device) in fits):
            s, b = fits[(core, device)]
            axis.plot(dense, s + b * dense, **figstyle.reference_style(
                label=r"Modèle $S + b \times$ bloc" if index == 0 else None))
        axis.set_xscale("log", base=2)
        axis.set_xticks(ticks, [size_label(c) for c in ticks])
        axis.xaxis.set_minor_locator(NullLocator())
        readable_log_axis(axis, *values, top_pad=3)   # place réservée à la légende
        axis.set(xlabel="Taille du bloc", ylabel="Coût par appel (ns)")
        axis.legend()
        figstyle.panel_title(axis, letter, title)

    for core in CORES:
        for device in DEVICES:
            if (core, device, chunks[0]) not in table:
                continue
            per_byte = np.array([table[(core, device, c)][1] / c for c in chunks])
            byte_axis.plot(x, per_byte, color=CORE_COLOR[core], linestyle=DEVICE_STYLE[device],
                           marker=CORE_MARKER[core], markersize=2.4)
    handles = [Line2D([], [], color=CORE_COLOR[c], marker=CORE_MARKER[c], markersize=2.4, label=CORE_LABELS[c])
               for c in CORES]
    handles += [Line2D([], [], color=figstyle.INK, linestyle=DEVICE_STYLE[d], label=DEVICES[d]) for d in DEVICES]
    byte_axis.set_xscale("log", base=2)
    byte_axis.set_xticks(ticks, [size_label(c) for c in ticks])
    byte_axis.xaxis.set_minor_locator(NullLocator())
    byte_axis.set_xlabel("Taille du bloc")
    byte_axis.set_yscale("log")
    figstyle.log_axis(byte_axis, "y")
    byte_axis.set_ylabel("Coût par octet (ns)")
    byte_axis.legend(handles=handles)
    figstyle.panel_title(byte_axis, "c", "Coût par octet")
    figstyle.save(figure, path)


SHARES = {}


def table_share(table, core, device, chunk):
    return SHARES.get((core, device, chunk), float("nan"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--reports", type=Path, required=True)
    parser.add_argument("--figures", type=Path)
    args = parser.parse_args()

    processes = load(args.directory)
    groups = defaultdict(list)
    for process in processes:
        groups[process["core"]].append(process)
    groups = {core: groups[core] for core in CORES if core in groups}
    rows, table = summary_rows(groups)
    for core, selected in groups.items():
        for key in selected[0]["share"]:
            shares = [p["share"][key] for p in selected if np.isfinite(p["share"][key])]
            if shares:
                SHARES[(core,) + key] = float(np.median(shares))
    chunks = sorted({chunk for (label, chunk) in processes[0]["cost"] if label == "write_dev_null"})
    model, fits = model_rows(table, chunks)

    prefix = str(args.reports)
    write_csv(Path(f"{prefix}-costs.csv"), rows)
    write_csv(Path(f"{prefix}-ratios.csv"), ratio_rows(groups))
    write_csv(Path(f"{prefix}-model.csv"), model)
    write_csv(Path(f"{prefix}-meta.csv"), [{"core": c, "processes": len(g),
                                            "stdio_default_buffer": g[0]["meta"]["stdio_default_buffer"],
                                            "max_involuntary_switches": max(int(p["meta"]["involuntary_switches"]) for p in g)}
                                           for c, g in groups.items()])
    if args.figures is not None:
        figstyle.use("times")
        plot_entry(table, Path(f"{args.figures}-entry.pdf"))
        plot_batching(table, fits, chunks, Path(f"{args.figures}-batching.pdf"))
    print(f"processus={len(processes)}")


if __name__ == "__main__":
    main()
