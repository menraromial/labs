#!/usr/bin/env python3

import argparse
import csv
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

# Style partagé des figures : voir STYLE_FIGURES.md à la racine du dépôt.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

# Chaque entité garde la même couleur et le même marqueur dans tous les panneaux.
ENTITIES = {
    "consecutive_reads": ("Lecture isolée", 0),
    "batched_reads": ("Lecture en lot", 1),
    "busy_cpu": ("Calcul", 2),
    "sleep": ("Attente", 3),
}
ELAPSED, CPU = "-", "--"


def percentile(values, probability):
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def write_summary(grouped, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["variant", "metric", "n", "min_ns", "median_ns", "mean_ns", "p95_ns", "max_ns"]
    summaries = []
    for variant, samples in grouped.items():
        metrics = [("elapsed", [int(row["elapsed_ns"]) for row in samples])]
        if variant in {"sleep", "busy_cpu"}:
            metrics.append(("cpu", [int(row["cpu_ns"]) for row in samples]))
        if variant == "batched_reads":
            metrics = [("per_read", [int(row["value_ns"]) for row in samples])]
        for metric, values in metrics:
            summaries.append({
                "variant": variant,
                "metric": metric,
                "n": len(values),
                "min_ns": min(values),
                "median_ns": round(statistics.median(values)),
                "mean_ns": round(statistics.fmean(values)),
                "p95_ns": round(percentile(values, 0.95)),
                "max_ns": max(values),
            })
    with path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        writer.writerows(summaries)


def read_targets(grouped, args):
    """Durées demandées (ns) : colonnes du CSV, sinon options explicites.

    Les CSV antérieurs à l'ajout des colonnes de paramètres n'en contiennent pas ;
    la cible n'est alors jamais devinée.
    """
    targets = {}
    for variant, column, option in (("sleep", "sleep_target_ns", args.sleep_target_ms),
                                    ("busy_cpu", "busy_target_ns", args.busy_target_ms)):
        first = grouped[variant][0]
        if first.get(column):
            targets[variant] = int(first[column])
        elif option is not None:
            targets[variant] = option * 1_000_000
        else:
            raise SystemExit(f"colonne {column} absente : préciser --{column[:-3].replace('_', '-')}-ms")
    return targets


def plot(grouped, targets, path):
    try:
        import numpy as np
        import figstyle
    except ImportError as error:
        raise SystemExit("matplotlib et numpy sont requis pour la figure") from error

    figstyle.use("times")

    def column(variant, field, scale):
        return np.array([int(row[field]) for row in grouped[variant]]) / scale

    def style(variant, **kwargs):
        label, slot = ENTITIES[variant]
        return {"color": figstyle.PALETTE[slot], "label": label, **kwargs}

    single_ns = column("consecutive_reads", "value_ns", 1)
    batch_ns = column("batched_reads", "value_ns", 1)
    sleep_target = targets["sleep"]
    busy_target = targets["busy_cpu"]

    figure, ((body, tail), (split, overshoot)) = figstyle.subplots(2, 2, height=3.15)

    # (a) Corps de la distribution sur un axe linéaire, rogné au-delà du p99,9.
    # Les valeurs rognées ne sont pas supprimées : elles apparaissent en (b).
    figstyle.ecdf(body, single_ns, **style("consecutive_reads", linestyle=ELAPSED))
    figstyle.ecdf(body, batch_ns, **style("batched_reads", linestyle=CPU))
    upper = 10 * math.ceil(1.15 * max(np.quantile(single_ns, 0.999), batch_ns.max()) / 10)
    lower = 5 * math.floor(0.9 * min(single_ns.min(), batch_ns.min()) / 5)
    hidden = int((single_ns > upper).sum())
    body.set_xlim(lower, upper)
    body.set_ylim(0, 1.02)
    body.set(xlabel="Durée par lecture (ns)", ylabel="Probabilité cumulée")
    figstyle.fixed_ticks(body, "y", (0, 0.25, 0.5, 0.75, 1))
    if hidden:
        share = figstyle.french_number(100 * hidden / single_ns.size, 2)
        noun = "valeur" if hidden == 1 else "valeurs"
        body.text(0.97, 0.5, f"{hidden} {noun} > {upper} ns\n({share} %), voir (b)",
                  transform=body.transAxes, ha="right", va="center",
                  fontsize=6, color=figstyle.MUTED, linespacing=1.15)
    body.legend()
    figstyle.panel_title(body, "a", "Lecture d'horloge : corps")

    # (b) Traîne : fonction de survie en log-log, jusqu'à la valeur maximale.
    figstyle.ccdf(tail, single_ns, **style("consecutive_reads", linestyle=ELAPSED))
    figstyle.ccdf(tail, batch_ns, **style("batched_reads", linestyle=CPU))
    figstyle.log_axis(tail, "x")
    figstyle.log_axis(tail, "y")
    tail.set_xlim(*figstyle.decade_limits(single_ns, batch_ns, pad=1))
    tail.set_ylim(0.4 / single_ns.size, 1.6)
    peak = single_ns.max()
    tail.plot([peak], [1 / single_ns.size], marker="o", markersize=3,
              color=figstyle.PALETTE[ENTITIES["consecutive_reads"][1]])
    tail.annotate(f"max. {figstyle.duration_ns(peak)}",
                  xy=(peak, 1 / single_ns.size), xytext=(-2, 9),
                  textcoords="offset points", ha="right", va="bottom",
                  fontsize=6, color=figstyle.MUTED)
    tail.set(xlabel="Durée par lecture (ns)", ylabel=r"$P(X \geq x)$")
    tail.legend()
    figstyle.panel_title(tail, "b", "Lecture d'horloge : traîne")

    # (c) Chaque répétition est un point (CPU, écoulé) ; la diagonale marque
    # l'égalité. L'écart vertical à la diagonale est du temps sans CPU.
    points = {variant: (column(variant, "cpu_ns", 1e6), column(variant, "elapsed_ns", 1e6))
              for variant in ("busy_cpu", "sleep")}
    limits = figstyle.decade_limits(*(axis for pair in points.values() for axis in pair))
    split.plot(limits, limits, label="Écoulé = CPU", **figstyle.reference_style())
    for variant, (cpu_ms, elapsed_ms) in points.items():
        _, slot = ENTITIES[variant]
        split.scatter(cpu_ms, elapsed_ms, s=11, alpha=0.7, marker=figstyle.MARKERS[slot],
                      linewidths=0, zorder=3, **style(variant))
    for which in ("x", "y"):
        figstyle.log_axis(split, which)
    split.set_xlim(*limits)
    split.set_ylim(*limits)
    sleep_cpu, sleep_elapsed = (statistics.median(axis) for axis in points["sleep"])
    ratio = figstyle.significant(sleep_elapsed / sleep_cpu, 2)
    # La flèche mesure l'écart vertical à la diagonale : le temps passé hors CPU.
    split.annotate("", xy=(sleep_cpu, sleep_elapsed / 1.6), xytext=(sleep_cpu, sleep_cpu * 1.6),
                   arrowprops={"arrowstyle": "->", "color": figstyle.MUTED,
                               "linewidth": 0.6, "shrinkA": 0, "shrinkB": 0})
    split.text(sleep_cpu * 1.5, math.sqrt(sleep_cpu * sleep_elapsed),
               rf"écoulé $\approx$ {figstyle.french_number(ratio)} × CPU" "\n(médianes, attente)",
               ha="left", va="center", fontsize=6, color=figstyle.MUTED, linespacing=1.15)
    split.set(xlabel="Temps CPU (ms)", ylabel="Temps écoulé (ms)")
    split.legend()
    figstyle.panel_title(split, "c", "Écoulé contre CPU")

    # (d) Dépassement de la durée demandée, par répétition.
    series = [
        ("busy_cpu", "elapsed_ns", busy_target, ELAPSED, "Calcul, écoulé"),
        ("busy_cpu", "cpu_ns", busy_target, CPU, "Calcul, CPU"),
        ("sleep", "elapsed_ns", sleep_target, ELAPSED, "Attente, écoulé"),
    ]
    excesses = []
    for variant, field, target, linestyle, label in series:
        excess_us = (column(variant, field, 1) - target) / 1000
        if (excess_us <= 0).any():
            figstyle.warn(f"{label} : {int((excess_us <= 0).sum())} dépassement(s) <= 0 "
                          "non représentables sur l'axe logarithmique")
        excess_us = excess_us[excess_us > 0]
        excesses.append(excess_us)
        figstyle.ecdf(overshoot, excess_us, **style(variant, linestyle=linestyle, label=label))
    figstyle.log_axis(overshoot, "x")
    overshoot.set_xlim(*figstyle.decade_limits(*excesses, pad=1))
    overshoot.set_ylim(0, 1.02)
    overshoot.set(xlabel=r"Dépassement $\delta$ (µs)", ylabel="Probabilité cumulée")
    figstyle.fixed_ticks(overshoot, "y", (0, 0.25, 0.5, 0.75, 1))
    overshoot.legend()
    figstyle.panel_title(overshoot, "d", "Dépassement de la cible")

    figstyle.save(figure, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=Path)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--figure", type=Path, required=True)
    parser.add_argument("--sleep-target-ms", type=int,
                        help="attente demandée, si le CSV ne la contient pas")
    parser.add_argument("--busy-target-ms", type=int,
                        help="temps CPU visé, si le CSV ne le contient pas")
    args = parser.parse_args()

    with args.raw.open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["variant"]].append(row)

    write_summary(grouped, args.summary)
    plot(grouped, read_targets(grouped, args), args.figure)


if __name__ == "__main__":
    main()
