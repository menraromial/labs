#!/usr/bin/env python3
"""Résumés et figures du projet B1.

Règles fixées avant la campagne (README, section 7) : unité statistique le
processus ; coût par élément médian sur les tours hors échauffement ; résumé
entre processus par médiane, écart interquartile et bootstrap percentile à
95 % ; pente log-log sur les médianes entre processus, seuil -0,5 ; modèle
c + F/n sur les tailles 64 à 65 536 ; contrôles par processus en médiane sur les
tailles ; corrélation de Spearman entre coût normalisé et fréquence.
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

BOOTSTRAP_SAMPLES = 10_000
BOOTSTRAP_SEED = 20260916
CONSTANT_WORK_SLOPE = -0.5
MODEL_MAX_N = 65_536
REFERENCE_N = 65_536
AA_GAP = 0.05
COMPILERS = ("gcc", "clang")
COMPILER_LABELS = {"gcc": "GCC", "clang": "Clang"}
LEVELS = ("O0", "O1", "O2", "O3")
KERNEL_OF = {"sum_array": "sum_array", "sum_array_bis": "sum_array",
             "sum_array_twice": "sum_array_twice", "sum_discarded": "sum_discarded",
             "sum_indices": "sum_indices"}


def level_color(level):
    return figstyle.PALETTE[LEVELS.index(level)]


def level_marker(level):
    return figstyle.MARKERS[LEVELS.index(level)]


def fmt(value, digits=4):
    return f"{value:.{digits}f}" if np.isfinite(value) else ""


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------- lecture

def load(directory):
    """Renvoie {run_id: processus} avec, pour chaque (mesure, n), le coût médian par élément."""
    processes = {}
    for planned in read_csv(directory / "plan.csv"):
        run_id = int(planned["run_id"])
        costs, per_call, calls = defaultdict(list), defaultdict(list), {}
        for row in read_csv(directory / f"run-{run_id:03d}.csv"):
            if row["phase"] != "measure":
                continue
            n, count, elapsed = int(row["n"]), int(row["calls"]), int(row["elapsed_ns"])
            key = (row["label"], n)
            costs[key].append(elapsed / (count * n))
            per_call[key].append(elapsed / count)
            calls[key] = count
        meta = read_csv(directory / f"run-{run_id:03d}-meta.csv")[0]
        processes[run_id] = {
            "compiler": planned["compiler"],
            "level": planned["level"],
            "cost": {key: float(np.median(v)) for key, v in costs.items()},
            "per_call": {key: float(np.median(v)) for key, v in per_call.items()},
            "calls": calls,
            "meta": meta,
        }
    return processes


def by_binary(processes):
    groups = defaultdict(list)
    for _, process in sorted(processes.items()):
        groups[(process["compiler"], process["level"])].append(process)
    return groups


# ---------------------------------------------------------------- statistiques

def bootstrap_median(values):
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    indices = rng.integers(0, values.size, size=(BOOTSTRAP_SAMPLES, values.size))
    low, high = np.percentile(np.median(values[indices], axis=1), [2.5, 97.5])
    return float(np.median(values)), float(low), float(high)


def bootstrap_ratio(numerator, denominator):
    """Rapport des médianes de deux groupes indépendants de processus, avec IC bootstrap."""
    numerator, denominator = np.asarray(numerator, float), np.asarray(denominator, float)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    top = np.median(numerator[rng.integers(0, numerator.size, (BOOTSTRAP_SAMPLES, numerator.size))], axis=1)
    bottom = np.median(denominator[rng.integers(0, denominator.size, (BOOTSTRAP_SAMPLES, denominator.size))], axis=1)
    low, high = np.percentile(top / bottom, [2.5, 97.5])
    return float(np.median(numerator) / np.median(denominator)), float(low), float(high)


def spearman(x, y):
    def ranks(values):
        values = np.asarray(values, float)
        order = values.argsort()
        result = np.empty(values.size)
        result[order] = np.arange(values.size)
        for value in np.unique(values):  # rangs moyens pour les ex aequo
            mask = values == value
            result[mask] = result[mask].mean()
        return result
    rx, ry = ranks(x), ranks(y)
    return float(np.corrcoef(rx, ry)[0, 1])


def sizes_of(processes):
    return sorted({n for p in processes.values() for (_, n) in p["cost"]})


# ---------------------------------------------------------------- analyses

def summarize_costs(groups, sizes):
    rows, curves = [], {}
    for (compiler, level), selected in sorted(groups.items()):
        for label in KERNEL_OF:
            medians, q25s, q75s, calls = [], [], [], []
            for n in sizes:
                values = [p["cost"][(label, n)] for p in selected]
                center, low, high = bootstrap_median(values)
                per_call = float(np.median([p["per_call"][(label, n)] for p in selected]))
                q25, q75 = np.quantile(values, [0.25, 0.75])
                medians.append(center)
                q25s.append(q25)
                q75s.append(q75)
                calls.append(per_call)
                rows.append({"compiler": compiler, "level": level, "label": label, "n": n,
                             "processes": len(values), "calls_per_sample": selected[0]["calls"][(label, n)],
                             "median_ns_per_element": fmt(center, 6), "ci95_low": fmt(low, 6),
                             "ci95_high": fmt(high, 6), "q25_ns_per_element": fmt(q25, 6),
                             "q75_ns_per_element": fmt(q75, 6),
                             "between_process_relative_iqr": fmt((q75 - q25) / center, 4),
                             "median_ns_per_call": fmt(per_call, 3),
                             "median_throughput_elements_per_s": fmt(1e9 / center, 0)})
            curves[(compiler, level, label)] = {"median": np.array(medians), "q25": np.array(q25s),
                                                "q75": np.array(q75s), "per_call": np.array(calls)}
    return rows, curves


def slope_rows(curves, sizes, assembly):
    rows, slopes = [], {}
    x = np.log2(np.asarray(sizes, dtype=float))
    for (compiler, level, label), curve in sorted(curves.items()):
        slope = float(np.polyfit(x, np.log2(curve["median"]), 1)[0])
        slopes[(compiler, level, label)] = slope
        kernel = KERNEL_OF[label]
        has_loop = assembly[(compiler, level, kernel)]["has_loop"] == "1"
        constant = slope < CONSTANT_WORK_SLOPE
        rows.append({"compiler": compiler, "level": level, "label": label, "slope": fmt(slope, 3),
                     "measured_work": "constant" if constant else "proportionnel",
                     "assembly_has_loop": int(has_loop),
                     "agreement": int(constant != has_loop)})
    return rows, slopes


def model_rows(groups, sizes):
    rows = []
    small = [n for n in sizes if n <= MODEL_MAX_N]
    for (compiler, level), selected in sorted(groups.items()):
        medians = [np.median([p["cost"][("sum_array", n)] for p in selected]) for n in small]
        design = np.column_stack([np.ones(len(small)), 1 / np.asarray(small, float)])
        (c, f), *_ = np.linalg.lstsq(design, np.asarray(medians), rcond=None)
        rows.append({"compiler": compiler, "level": level, "c_ns_per_element": fmt(c, 4),
                     "F_ns_per_call": fmt(f, 2), "sizes": f"{small[0]}-{small[-1]}"})
    return rows


def control_rows(groups, sizes):
    rows, values = [], {}
    for (compiler, level), selected in sorted(groups.items()):
        aa = [float(np.median([p["cost"][("sum_array_bis", n)] / p["cost"][("sum_array", n)] for n in sizes]))
              for p in selected]
        twice = [float(np.median([p["cost"][("sum_array_twice", n)] / p["cost"][("sum_array", n)] for n in sizes]))
                 for p in selected]
        values[(compiler, level)] = {"aa": aa, "twice": twice}
        row = {"compiler": compiler, "level": level, "processes": len(selected)}
        for name, data in (("aa", aa), ("twice", twice)):
            center, low, high = bootstrap_median(data)
            row.update({f"{name}_median": fmt(center), f"{name}_ci95_low": fmt(low),
                        f"{name}_ci95_high": fmt(high), f"{name}_min": fmt(min(data)),
                        f"{name}_max": fmt(max(data))})
        row["aa_share_gap_over_5pct"] = fmt(float(np.mean(np.abs(np.asarray(aa) - 1) > AA_GAP)), 3)
        row["max_involuntary_switches"] = max(int(p["meta"]["involuntary_switches"]) for p in selected)
        row["max_minor_faults"] = max(int(p["meta"]["minor_faults"]) for p in selected)
        rows.append(row)
    return rows, values


def speedup_rows(groups, sizes):
    rows, values = [], {}
    for compiler in COMPILERS:
        baseline = groups[(compiler, "O0")]
        for level in LEVELS:
            for n in (REFERENCE_N, sizes[-1]):
                slow = [p["cost"][("sum_array", n)] for p in baseline]
                fast = [p["cost"][("sum_array", n)] for p in groups[(compiler, level)]]
                center, low, high = bootstrap_ratio(slow, fast)
                values[(compiler, level, n)] = (center, low, high)
                rows.append({"compiler": compiler, "level": level, "n": n,
                             "speedup_vs_O0": fmt(center, 3), "ci95_low": fmt(low, 3),
                             "ci95_high": fmt(high, 3)})
    # Comparaison entre compilateurs au même niveau, à la taille de référence.
    for level in LEVELS:
        gcc = [p["cost"][("sum_array", REFERENCE_N)] for p in groups[("gcc", level)]]
        clang = [p["cost"][("sum_array", REFERENCE_N)] for p in groups[("clang", level)]]
        center, low, high = bootstrap_ratio(gcc, clang)
        rows.append({"compiler": "gcc/clang", "level": level, "n": REFERENCE_N,
                     "speedup_vs_O0": fmt(center, 3), "ci95_low": fmt(low, 3), "ci95_high": fmt(high, 3)})
    return rows, values


def frequency_rows(groups):
    rows = []
    for (compiler, level), selected in sorted(groups.items()):
        reference = np.median([p["cost"][("sum_array", REFERENCE_N)] for p in selected])
        for process in selected:
            meta = process["meta"]
            rows.append({"compiler": compiler, "level": level, "run_id": meta["run_id"],
                         "frequency_before_khz": meta["frequency_before_khz"],
                         "frequency_after_khz": meta["frequency_after_khz"],
                         "normalized_cost": fmt(process["cost"][("sum_array", REFERENCE_N)] / reference, 4)})
    usable = [r for r in rows if r["frequency_after_khz"]]
    rho = spearman([float(r["frequency_after_khz"]) for r in usable],
                   [float(r["normalized_cost"]) for r in usable]) if len(usable) > 2 else float("nan")
    summary = [{"processes": len(usable), "spearman_rho_frequency_after_vs_cost": fmt(rho, 3)}]
    return rows, summary


# ---------------------------------------------------------------- figures

def size_ticks(axis, sizes):
    figstyle.fixed_ticks(axis, "x", [n for n in sizes if int(np.log2(n)) % 4 == 2])


def readable_log_ticks(*groups):
    data = np.concatenate([np.asarray(g, dtype=float).ravel() for g in groups])
    data = data[np.isfinite(data) & (data > 0)]
    low, high = data.min() / 1.5, data.max() * 1.5
    ticks = [m * 10.0 ** e for e in range(-8, 12) for m in (1, 2, 5)]
    chosen = [t for t in ticks if low <= t <= high]
    if len(chosen) > 7:  # trop de décennies : puissances de dix seulement
        chosen = [t for t in chosen if np.isclose(np.log10(t) % 1, 0) or np.isclose(np.log10(t) % 1, 1)]
    return chosen


def log_log_axis(axis, sizes, values):
    axis.set_xscale("log", base=2)
    axis.set_yscale("log")
    size_ticks(axis, sizes)
    data = np.concatenate([np.asarray(v, dtype=float).ravel() for v in values])
    if data.max() / data.min() > 1_000:  # plus de trois décennies : puissances de dix
        figstyle.log_axis(axis, "y")
    else:
        figstyle.fixed_ticks(axis, "y", readable_log_ticks(values))


def plot_scaling(curves, sizes, path):
    figure, axes = figstyle.subplots(2, 3, height=3.9)
    x = np.asarray(sizes, dtype=float)
    letters = iter("abcdef")
    for row, compiler in enumerate(COMPILERS):
        duration, cost, throughput = axes[row]
        for level in LEVELS:
            curve = curves[(compiler, level, "sum_array")]
            style = {"color": level_color(level), "marker": level_marker(level), "markersize": 2.6}
            duration.plot(x, curve["per_call"], label=f"-{level}", **style)
            cost.fill_between(x, curve["q25"], curve["q75"], color=level_color(level),
                              alpha=0.18, linewidth=0)
            cost.plot(x, curve["median"], **style)
            throughput.plot(x, 1 / curve["median"], **style)  # 1/ns = 10^9 éléments/s
        name = COMPILER_LABELS[compiler]
        everything = [curves[(compiler, l, "sum_array")] for l in LEVELS]
        log_log_axis(duration, sizes, [c["per_call"] for c in everything])
        log_log_axis(cost, sizes, [c["median"] for c in everything])
        throughput.set_xscale("log", base=2)
        size_ticks(throughput, sizes)
        throughput.set_ylim(0, max(float(np.max(1 / c["median"])) for c in everything) * 1.1)
        figstyle.french_ticks(throughput, "y")
        duration.set(ylabel="Durée d'un appel (ns)")
        cost.set(ylabel="Coût par élément (ns)")
        throughput.set(ylabel=r"Débit ($10^9$ éléments/s)")
        for axis in (duration, cost, throughput):
            axis.set_xlabel("Taille n (éléments)")
        duration.legend(title=name, title_fontsize=6.5)
        figstyle.panel_title(duration, next(letters), f"{name} : durée d'un appel")
        figstyle.panel_title(cost, next(letters), f"{name} : coût par élément")
        figstyle.panel_title(throughput, next(letters), f"{name} : débit")
    figstyle.save(figure, path)


def plot_eliminated(curves, sizes, slopes, assembly, path):
    figure, axes = figstyle.subplots(2, 2, height=4.6)
    x = np.asarray(sizes, dtype=float)
    letters = iter("abcd")
    titles = {"sum_discarded": "somme ignorée", "sum_indices": "somme des indices"}
    for row, label in enumerate(("sum_discarded", "sum_indices")):
        for column, compiler in enumerate(COMPILERS):
            axis = axes[row][column]
            values = []
            for level in LEVELS:
                curve = curves[(compiler, level, label)]
                values.append(curve["q25"])
                values.append(curve["q75"])
                loop = assembly[(compiler, level, label)]["has_loop"] == "1"
                slope = figstyle.french_number(slopes[(compiler, level, label)], 2).replace("-", "−")
                axis.fill_between(x, curve["q25"], curve["q75"], color=level_color(level),
                                  alpha=0.18, linewidth=0)
                axis.plot(x, curve["median"], color=level_color(level), marker=level_marker(level),
                          markersize=2.6, label=f"-{level} : {slope} ; {'oui' if loop else 'non'}")
            axis.set_xscale("log", base=2)
            axis.set_yscale("log")
            size_ticks(axis, sizes)
            figstyle.log_axis(axis, "y")
            low, high = figstyle.decade_limits(*values, pad=1)
            axis.set_ylim(low, high * 1000)  # marge réservée à la légende, au-dessus des courbes
            axis.set(xlabel="Taille n (éléments)", ylabel="Coût apparent par élément (ns)")
            axis.legend(title="Niveau : pente ; boucle", title_fontsize=6.5)
            figstyle.panel_title(axis, next(letters), f"{COMPILER_LABELS[compiler]} : {titles[label]}")
    figstyle.save(figure, path)


def binary_axis(axis):
    positions = [(c, l) for c in COMPILERS for l in LEVELS]
    axis.set_xticks(range(len(positions)),
                    [f"{COMPILER_LABELS[c]}\n-{l}" for c, l in positions])
    axis.tick_params(axis="x", length=0)
    axis.grid(axis="x", visible=False)
    axis.set_xlim(-0.6, len(positions) - 0.4)
    axis.axvline(3.5, color=figstyle.GRID, linewidth=0.8, zorder=0)
    return positions


def ratio_strip(axis, controls, key, expected):
    positions = binary_axis(axis)
    done = set()
    for x, (compiler, level) in enumerate(positions):
        data = controls[(compiler, level)][key]
        figstyle.strip(axis, x - 0.1, data, width=0.12, seed=x, color=level_color(level),
                       marker=level_marker(level), s=8,
                       label=f"-{level}" if level not in done else None)
        done.add(level)
        center, low, high = bootstrap_median(data)
        figstyle.interval(axis, x + 0.22, center, low, high, markersize=2.6, capsize=1.6,
                          label="Médiane, IC 95 %" if x == 0 else None)
    axis.axhline(expected, **figstyle.reference_style())
    everything = np.concatenate([controls[p][key] for p in positions] + [[expected]])
    span = max(everything.max() - expected, expected - everything.min())
    axis.set_ylim(expected - span * 1.4, expected + span * 2.6)
    figstyle.french_ticks(axis, "y")


def plot_controls(controls, speedups, frequency, sizes, path):
    figure, ((same, twice), (gain, freq)) = figstyle.subplots(2, 2, height=3.8)

    ratio_strip(same, controls, "aa", 1)
    same.set_ylabel("sum_array_bis / sum_array")
    same.legend(ncols=2)
    figstyle.panel_title(same, "a", "Contrôle A/A : rapport vrai 1")

    ratio_strip(twice, controls, "twice", 2)
    twice.set_ylabel("sum_array_twice / sum_array")
    twice.legend(ncols=2)
    figstyle.panel_title(twice, "b", "Contrôle positif : deux parcours")

    positions = binary_axis(gain)
    for x, (compiler, level) in enumerate(positions):
        for n, filled in ((REFERENCE_N, True), (sizes[-1], False)):
            center, low, high = speedups[(compiler, level, n)]
            offset = -0.13 if filled else 0.13
            figstyle.interval(gain, x + offset, center, low, high, color=level_color(level),
                              marker=level_marker(level), markersize=3.2, capsize=1.6,
                              markerfacecolor=level_color(level) if filled else "white",
                              label=None)
    gain.axhline(1, **figstyle.reference_style())
    gain.set_yscale("log")
    top = max(v[2] for v in speedups.values())
    figstyle.fixed_ticks(gain, "y", [t for t in (1, 2, 5, 10, 20, 50) if t <= top * 1.6])
    gain.set_ylim(0.8, top * 1.6)
    gain.set_ylabel("Accélération par rapport à -O0")
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], color=figstyle.INK, marker="o", linestyle="none", markersize=3.2,
                      label=f"n = {figstyle.french_number(REFERENCE_N)} (512 Kio)"),
               Line2D([], [], color=figstyle.INK, marker="o", markerfacecolor="white",
                      linestyle="none", markersize=3.2,
                      label=f"n = {figstyle.french_number(sizes[-1])} (32 Mio)")]
    gain.legend(handles=handles)
    figstyle.panel_title(gain, "c", "Gain d'optimisation : sum_array")

    done = set()
    for row in frequency:
        if not row["frequency_after_khz"]:
            continue
        level = row["level"]
        freq.scatter(float(row["frequency_after_khz"]) / 1000, float(row["normalized_cost"]),
                     color=level_color(level), marker=level_marker(level), s=9, alpha=0.7,
                     linewidths=0, label=f"-{level}" if level not in done else None)
        done.add(level)
    freq.axhline(1, **figstyle.reference_style())
    figstyle.french_ticks(freq, "y")
    freq.set(xlabel="scaling_cur_freq après la mesure (MHz)",
             ylabel="Coût / médiane du binaire")
    freq.legend()
    figstyle.panel_title(freq, "d", "Fréquence et coût, n = 65 536")
    figstyle.save(figure, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--assembly", type=Path, required=True)
    parser.add_argument("--reports", type=Path, required=True)
    parser.add_argument("--figures", type=Path)
    args = parser.parse_args()

    processes = load(args.directory)
    sizes = sizes_of(processes)
    groups = by_binary(processes)
    assembly = {(r["compiler"], r["level"], r["kernel"]): r for r in read_csv(args.assembly)}
    assembly.update({(c, l, "sum_array_bis"): assembly[(c, l, "sum_array")]
                     for c, l, k in list(assembly) if k == "sum_array"})

    cost_table, curves = summarize_costs(groups, sizes)
    slopes_table, slopes = slope_rows(curves, sizes, assembly)
    controls_table, controls = control_rows(groups, sizes)
    speedup_table, speedups = speedup_rows(groups, sizes)
    frequency_table, frequency_summary = frequency_rows(groups)

    prefix = str(args.reports)
    write_csv(Path(f"{prefix}-costs.csv"), cost_table)
    write_csv(Path(f"{prefix}-slopes.csv"), slopes_table)
    write_csv(Path(f"{prefix}-model.csv"), model_rows(groups, sizes))
    write_csv(Path(f"{prefix}-controls.csv"), controls_table)
    write_csv(Path(f"{prefix}-speedup.csv"), speedup_table)
    write_csv(Path(f"{prefix}-frequency.csv"), frequency_table)
    write_csv(Path(f"{prefix}-frequency-summary.csv"), frequency_summary)

    if args.figures is not None:
        figstyle.use("times")
        plot_scaling(curves, sizes, Path(f"{args.figures}-scaling.pdf"))
        plot_eliminated(curves, sizes, slopes, assembly, Path(f"{args.figures}-eliminated.pdf"))
        plot_controls(controls, speedups, frequency_table, sizes, Path(f"{args.figures}-controls.pdf"))
    agreement = sum(int(r["agreement"]) for r in slopes_table)
    print(f"processus={len(processes)} accord pente/assembleur={agreement}/{len(slopes_table)}")


if __name__ == "__main__":
    main()
