#!/usr/bin/env python3
"""Résumés et figures du projet D2.

Règles fixées avant la campagne (README, section 7) : unité statistique le
processus ; médiane et 99e centile par processus des latences par opération des
tours mesurés ; débit séquentiel : médiane par processus sur les tours ; médiane et
bootstrap percentile à 95 % entre processus ; rapports par processus ; modèle
F + w × k par moindres carrés relatifs sur les médianes ; comptes de mécanisme par
opération en médiane sur les échantillons.
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
from matplotlib.ticker import FuncFormatter, NullLocator  # noqa: E402

BOOTSTRAP_SAMPLES = 10_000
BOOTSTRAP_SEED = 20260921
PAGE = 4096
BATCHES = (1, 4, 16, 64, 256)
GIB = 1 << 30

READ_SERIES = (("rand_read_warm", "Page en cache"), ("rand_read_cold", "Page retirée du cache"),
               ("rand_read_direct", "O_DIRECT"))
SEQ_SERIES = (("seq_read_warm", "En cache"), ("seq_read_cold", "Retiré\ndu cache"), ("seq_read_direct", "O_DIRECT"))
WRITE_SERIES = (("append_buffered", 0, "write seul"), ("tmpfs_append_fsync", 1, "write + fsync, tmpfs"),
                ("overwrite_fdatasync", 1, "réécriture + fdatasync"), ("overwrite_fsync", 1, "réécriture + fsync"),
                ("append_fsync", 1, "ajout + fsync"))
WRITE_STYLE = {"append_buffered": (figstyle.PALETTE[0], "-"), "tmpfs_append_fsync": (figstyle.MUTED, ":"),
               "overwrite_fdatasync": (figstyle.PALETTE[2], "-."), "overwrite_fsync": (figstyle.PALETTE[3], "--"),
               "append_fsync": (figstyle.PALETTE[1], "-")}
MECHANISM = ("device_reads", "device_read_sectors", "device_writes", "device_write_sectors", "device_flushes",
             "journal_commits", "voluntary_switches", "read_bytes", "write_bytes")


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


# ---------------------------------------------------------------- lecture

def load(directory):
    processes = []
    for planned in read_csv(directory / "plan.csv"):
        run_id = int(planned["run_id"])
        rows = read_csv(directory / f"run-{run_id:03d}.csv")
        measured = {int(r["sample"]): r for r in rows if r["phase"] == "measure"}
        latencies = defaultdict(list)
        with (directory / f"run-{run_id:03d}-ops.csv").open(newline="", encoding="utf-8") as source:
            for row in csv.DictReader(source):
                sample = measured.get(int(row["sample"]))
                if sample is not None:
                    latencies[(sample["label"], int(sample["param"]))].append(int(row["latency_ns"]))
        samples = defaultdict(list)
        for r in measured.values():
            samples[(r["label"], int(r["param"]))].append(r)
        processes.append({"run_id": run_id, "latencies": {k: np.asarray(v, dtype=float) for k, v in latencies.items()},
                          "samples": samples, "meta": read_csv(directory / f"run-{run_id:03d}-meta.csv")[0]})
    return processes


def per_process(process, key):
    """Statistiques d'un processus pour une mesure : latence médiane et 99e centile, débit, totaux."""
    rows = process["samples"][key]
    units = int(rows[0]["units_per_op"])
    stats = {"units": units}
    if key[0].startswith("seq"):
        rates = [int(r["ops"]) * units * PAGE / int(r["elapsed_ns"]) * 1e9 / GIB for r in rows]
        stats["throughput_gib_s"] = float(np.median(rates))
    else:
        values = process["latencies"][key]
        stats["median_ns"] = float(np.median(values))
        stats["p99_ns"] = float(np.percentile(values, 99))
        stats["record_ns"] = stats["median_ns"] / units if key[0] == "append_fsync" else stats["median_ns"]
    records = [int(r["ops"]) * units for r in rows]
    stats["sample_record_ns"] = float(np.median([int(r["elapsed_ns"]) / n for r, n in zip(rows, records)]))
    stats["with_deferred_record_ns"] = float(np.median(
        [(int(r["elapsed_ns"]) + int(r["deferred_ns"])) / n for r, n in zip(rows, records)]))
    stats["deferred_ns"] = float(np.median([int(r["deferred_ns"]) for r in rows]))
    return stats


# ---------------------------------------------------------------- analyses

def summary_rows(processes):
    rows, table = [], {}
    for key in sorted(processes[0]["samples"]):
        stats = [per_process(p, key) for p in processes]
        row = {"label": key[0], "param": key[1], "processes": len(stats), "units_per_op": stats[0]["units"]}
        for name in ("median_ns", "p99_ns", "record_ns", "throughput_gib_s", "deferred_ns",
                     "with_deferred_record_ns"):
            if name not in stats[0] or (name.startswith(("deferred", "with_deferred")) and key[0] != "append_buffered"):
                continue
            values = [s[name] for s in stats]
            center, low, high = bootstrap_median(values)
            table[key + (name,)] = (values, center, low, high)
            row.update({name: fmt(center, 4), f"{name}_ci95_low": fmt(low, 4), f"{name}_ci95_high": fmt(high, 4)})
        rows.append(row)
    return rows, table


def ratio(processes, name, top, bottom, statistic="median_ns", bottom_statistic=None):
    values = [per_process(p, top)[statistic] / per_process(p, bottom)[bottom_statistic or statistic]
              for p in processes]
    center, low, high = bootstrap_median(values)
    return {"ratio": name, "median": fmt(center, 3), "ci95_low": fmt(low, 3), "ci95_high": fmt(high, 3),
            "min": fmt(min(values), 3), "max": fmt(max(values), 3)}


def ratio_rows(processes):
    r = lambda label, param=0: (label, param)  # noqa: E731
    rows = [
        ratio(processes, "rand_read_cold/rand_read_warm", r("rand_read_cold"), r("rand_read_warm")),
        ratio(processes, "rand_read_cold p99/median", r("rand_read_cold"), r("rand_read_cold"), "p99_ns", "median_ns"),
        ratio(processes, "rand_read_direct/rand_read_cold", r("rand_read_direct"), r("rand_read_cold")),
        ratio(processes, "aa rand_read_cold_bis/rand_read_cold", r("rand_read_cold_bis"), r("rand_read_cold")),
        ratio(processes, "positive rand_read_direct_double/rand_read_direct", r("rand_read_direct_double"),
              r("rand_read_direct")),
        ratio(processes, "seq_read_warm/seq_read_cold (throughput)", r("seq_read_warm"), r("seq_read_cold"),
              "throughput_gib_s"),
        ratio(processes, "seq_read_direct/seq_read_cold (throughput)", r("seq_read_direct"), r("seq_read_cold"),
              "throughput_gib_s"),
        ratio(processes, "append_fsync_1/append_buffered", r("append_fsync", 1), r("append_buffered")),
        ratio(processes, "append_fsync_1/tmpfs_append_fsync", r("append_fsync", 1), r("tmpfs_append_fsync", 1)),
        ratio(processes, "overwrite_fdatasync/overwrite_fsync", r("overwrite_fdatasync", 1), r("overwrite_fsync", 1)),
        ratio(processes, "append_fdatasync/append_fsync_1", r("append_fdatasync", 1), r("append_fsync", 1)),
        ratio(processes, "overwrite_fsync/append_fsync_1", r("overwrite_fsync", 1), r("append_fsync", 1)),
        ratio(processes, "overwrite_odsync/overwrite_fdatasync", r("overwrite_odsync", 1), r("overwrite_fdatasync", 1)),
        ratio(processes, "overwrite_fdatasync_folio/overwrite_fdatasync", r("overwrite_fdatasync_folio", 1),
              r("overwrite_fdatasync", 1)),
        ratio(processes, "overwrite_odsync_folio/overwrite_odsync", r("overwrite_odsync_folio", 1),
              r("overwrite_odsync", 1)),
        ratio(processes, "aa overwrite_fdatasync_bis/overwrite_fdatasync", r("overwrite_fdatasync_bis", 1),
              r("overwrite_fdatasync", 1)),
        ratio(processes, "positive overwrite_fdatasync_double/overwrite_fdatasync", r("overwrite_fdatasync_double", 1),
              r("overwrite_fdatasync", 1)),
        ratio(processes, "per record append_fsync_256/append_fsync_1", r("append_fsync", 256), r("append_fsync", 1),
              "record_ns"),
        ratio(processes, "per record (append_buffered + fsync)/append_fsync_256", r("append_buffered"),
              r("append_fsync", 256), "with_deferred_record_ns", "sample_record_ns"),
    ]
    return rows


def model_rows(table):
    y = np.array([table[("append_fsync", k, "median_ns")][1] for k in BATCHES])
    x = np.asarray(BATCHES, dtype=float)
    design = np.column_stack([1 / y, x / y])        # F / y + w k / y = 1
    (fixed, per_record), *_ = np.linalg.lstsq(design, np.ones_like(y), rcond=None)
    fitted = fixed + per_record * x
    rows = [{"F_ns": fmt(fixed, 0), "w_ns_per_record": fmt(per_record, 0), "F_over_batch1": fmt(fixed / y[0], 3),
             "record_256_over_record_1": fmt(y[-1] / 256 / y[0], 4),
             "max_relative_residual": fmt(float(np.max(np.abs(fitted / y - 1))), 3)}]
    return rows, (fixed, per_record)


def mechanism_rows(processes):
    rows = []
    for key in sorted(processes[0]["samples"]):
        samples = [r for p in processes for r in p["samples"][key]]
        row = {"label": key[0], "param": key[1], "samples": len(samples)}
        for field in MECHANISM + ("deferred_device_write_sectors", "deferred_device_flushes",
                                  "deferred_journal_commits"):
            per_op = np.array([int(r[field]) / int(r["ops"]) for r in samples], dtype=float)
            row[f"{field}_per_op_median"] = fmt(float(np.median(per_op)), 3)
            row[f"{field}_per_op_mean"] = fmt(float(np.mean(per_op)), 3)
        row["resident_after_median"] = fmt(float(np.median([int(r["resident_after"]) for r in samples])), 0)
        rows.append(row)
    return rows


# ---------------------------------------------------------------- figures

def duration_axis(axis, which="x"):
    """Axe logarithmique en durées lisibles : 1 µs, 10 µs, 100 µs, 1 ms..."""
    figstyle.log_axis(axis, which)
    labels = {1e3: "1 µs", 1e4: "10 µs", 1e5: "100 µs", 1e6: "1 ms", 1e7: "10 ms", 1e8: "100 ms", 1e2: "100 ns",
              1e9: "1 s"}
    target = axis.xaxis if which == "x" else axis.yaxis
    target.set_major_formatter(FuncFormatter(lambda v, _: labels.get(float(f"{v:.0e}"), "")))
    target.set_minor_formatter(FuncFormatter(lambda v, _: ""))


def pooled(processes, key):
    return np.concatenate([p["latencies"][key] for p in processes])


def plot_reads(processes, table, path):
    figure, (latency, throughput) = figstyle.subplots(1, 2, height=2.4)
    styles = ("-", "--", "-.")
    for index, (label, name) in enumerate(READ_SERIES):
        figstyle.ecdf(latency, pooled(processes, (label, 0)), color=figstyle.PALETTE[index],
                      linestyle=styles[index], label=name)
    duration_axis(latency, "x")
    latency.set(xlabel=r"Latence $t$ d'une lecture de 4 Kio", ylabel="Fraction des lectures")
    figstyle.fixed_ticks(latency, "y", (0, 0.25, 0.5, 0.75, 1))
    latency.set_ylim(0, 1.02)
    latency.legend(title="Pages distinctes au hasard")
    figstyle.panel_title(latency, "a", "Lectures aléatoires, toutes les opérations")

    everything = []
    for x, (label, name) in enumerate(SEQ_SERIES):
        values, center, low, high = table[(label, 0, "throughput_gib_s")]
        everything.extend(values)
        figstyle.strip(throughput, x - 0.08, values, width=0.06, seed=x, color=figstyle.PALETTE[x],
                       marker=figstyle.MARKERS[x], label="Un processus" if x == 0 else None)
        figstyle.interval(throughput, x + 0.12, center, low, high,
                          label="Médiane, IC 95 %" if x == 0 else None)
    throughput.set_xticks(range(len(SEQ_SERIES)), [name for _, name in SEQ_SERIES])
    throughput.tick_params(axis="x", length=0)
    throughput.grid(axis="x", visible=False)
    throughput.set_xlim(-0.6, len(SEQ_SERIES) - 0.4)
    throughput.set_yscale("log")
    low, high = min(everything) / 1.6, max(everything) * 3.0
    throughput.set_ylim(low, high)
    ticks = [m * 10.0 ** e for e in range(-2, 4) for m in (1, 2, 5) if low <= m * 10.0 ** e <= high]
    figstyle.fixed_ticks(throughput, "y", ticks)
    throughput.set_ylabel(r"Débit $D$ (Gio/s)")
    throughput.legend()
    figstyle.panel_title(throughput, "b", "Lecture séquentielle de 256 Mio")
    figstyle.save(figure, path)


def plot_writes(processes, table, fit, path):
    figure, (latency, batches) = figstyle.subplots(1, 2, height=2.6)
    for label, param, name in WRITE_SERIES:
        color, style = WRITE_STYLE[label]
        figstyle.ecdf(latency, pooled(processes, (label, param)), color=color, linestyle=style, label=name)
    duration_axis(latency, "x")
    latency.set(xlabel=r"Latence $t$ d'une opération (4 Kio)", ylabel="Fraction des opérations")
    figstyle.fixed_ticks(latency, "y", (0, 0.25, 0.5, 0.75, 1))
    latency.set_ylim(0, 1.02)
    latency.legend()
    figstyle.panel_title(latency, "a", "Écrire, avec ou sans persistance")

    x = np.asarray(BATCHES, dtype=float)
    center = np.array([table[("append_fsync", k, "record_ns")][1] for k in BATCHES])
    low = np.array([table[("append_fsync", k, "record_ns")][2] for k in BATCHES])
    high = np.array([table[("append_fsync", k, "record_ns")][3] for k in BATCHES])
    batches.fill_between(x, low, high, color=figstyle.PALETTE[1], alpha=0.2, linewidth=0)
    batches.plot(x, center, color=figstyle.PALETTE[1], marker="o", markersize=2.6,
                 label="Lot puis fsync, médiane et IC 95 %")
    fixed, per_record = fit
    dense = np.geomspace(1, 256, 100)
    batches.plot(dense, (fixed + per_record * dense) / dense,
                 **figstyle.reference_style(label=r"Modèle $(F + w\,k)\,/\,k$"))
    buffered = table[("append_buffered", 0, "with_deferred_record_ns")]
    batches.errorbar([256 * 1.35], [buffered[1]], yerr=[[buffered[1] - buffered[2]], [buffered[3] - buffered[1]]],
                     fmt="D", color=figstyle.PALETTE[0], markersize=3.2, capsize=2, linewidth=0.9, zorder=5,
                     label="write seuls puis un fsync")
    plain = table[("append_buffered", 0, "median_ns")][1]
    batches.axhline(plain, **figstyle.reference_style(linestyle="--", label="write seul, sans fsync"))
    batches.set_xscale("log", base=2)
    batches.set_xlim(0.75, 256 * 1.6)
    batches.set_xticks(BATCHES, [str(k) for k in BATCHES])
    batches.xaxis.set_minor_locator(NullLocator())
    batches.set_yscale("log")
    batches.set_ylim(plain / 2, center.max() * 8)
    duration_axis(batches, "y")
    batches.set(xlabel=r"Enregistrements par fsync $k$", ylabel=r"Coût par enregistrement $t(k)/k$")
    batches.legend()
    figstyle.panel_title(batches, "b", "Regrouper les demandes de persistance")
    figstyle.save(figure, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--reports", type=Path, required=True)
    parser.add_argument("--figures", type=Path)
    args = parser.parse_args()

    processes = load(args.directory)
    rows, table = summary_rows(processes)
    model, fit = model_rows(table)
    prefix = str(args.reports)
    write_csv(Path(f"{prefix}-summary.csv"), rows)
    write_csv(Path(f"{prefix}-ratios.csv"), ratio_rows(processes))
    write_csv(Path(f"{prefix}-model.csv"), model)
    write_csv(Path(f"{prefix}-mechanism.csv"), mechanism_rows(processes))
    write_csv(Path(f"{prefix}-meta.csv"), [{
        "processes": len(processes),
        "residency_retries": sum(int(p["meta"]["residency_retries"]) for p in processes),
        "max_involuntary_switches": max(int(p["meta"]["involuntary_switches"]) for p in processes),
        "operations_measured": sum(v.size for p in processes for v in p["latencies"].values())}])
    if args.figures is not None:
        figstyle.use("times")
        plot_reads(processes, table, Path(f"{args.figures}-reads.pdf"))
        plot_writes(processes, table, fit, Path(f"{args.figures}-writes.pdf"))
    print(f"processus={len(processes)}")


if __name__ == "__main__":
    main()
