"""Style commun des figures du laboratoire, calibré pour les articles A/A*.

Les règles sont énoncées dans ``STYLE_FIGURES.md`` à la racine du dépôt ; ce
module les applique. Toute modification doit mettre à jour les deux fichiers.

Usage minimal ::

    import figstyle
    figstyle.use()                       # avant toute création de figure
    fig, axes = figstyle.subplots(1, 2)
    ...
    figstyle.save(fig, "figures/ma-figure.pdf")
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib as mpl
import numpy as np

# Largeurs de texte des gabarits LaTeX (pouces). IEEE est légèrement plus large.
SINGLE_COLUMN = 3.33   # acmart sigconf, USENIX ; IEEEtran : 3.5
DOUBLE_COLUMN = 7.0    # acmart sigconf, USENIX ; IEEEtran : 7.16

# Palette catégorielle validée (Okabe-Ito, violet assombri pour le contraste).
# Ordre fixe : la couleur suit l'entité, jamais son rang dans un panneau.
PALETTE = ("#0072B2", "#D55E00", "#009E73", "#882E72")
INK = "#1A1A1A"
MUTED = "#5A5A5A"
REFERENCE = "#8A8A8A"
GRID = "#E4E4E4"

# Encodage secondaire, indispensable en niveaux de gris : un style par série.
LINESTYLES = ("-", "--", "-.", ":")
MARKERS = ("o", "s", "^", "D")

_FONT_PRESETS = {
    # USENIX (OSDI, NSDI, ATC, FAST) et IEEE : texte en Times.
    "times": {
        "font.serif": ["STIX Two Text", "TeX Gyre Termes", "Nimbus Roman",
                       "Liberation Serif", "DejaVu Serif"],
        "mathtext.fontset": "stix",
    },
    # ACM (SOSP, EuroSys, SIGCOMM, ASPLOS) : Linux Libertine.
    "acm": {
        "font.serif": ["Linux Libertine O", "STIX Two Text", "DejaVu Serif"],
        "mathtext.fontset": "custom",
        "mathtext.rm": "Linux Libertine O",
        "mathtext.it": "Linux Libertine O:italic",
        "mathtext.bf": "Linux Libertine O:bold",
    },
}


def _prefer_truetype() -> None:
    """Écarte les fichiers OpenType/CFF qui ont un équivalent TrueType.

    Avec ``pdf.fonttype = 42``, une police CFF est déclarée TrueType dans le PDF
    (« Mismatch between font type and embedded font file » dans ``pdffonts``).
    Sans ce filtre, le fichier retenu dépend de l'ordre du cache de matplotlib.
    """
    from matplotlib import font_manager

    manager = font_manager.fontManager

    def key(entry):
        return entry.name, entry.style, entry.variant, entry.weight, entry.stretch

    truetype = {key(entry) for entry in manager.ttflist if entry.fname.lower().endswith(".ttf")}
    manager.ttflist = [entry for entry in manager.ttflist
                       if not (entry.fname.lower().endswith(".otf") and key(entry) in truetype)]
    font_manager.FontManager._findfont_cached.cache_clear()


def use(preset: str = "times") -> None:
    """Applique le style du laboratoire à matplotlib."""
    if preset not in _FONT_PRESETS:
        raise ValueError(f"préréglage inconnu : {preset!r}")
    _prefer_truetype()
    mpl.rcParams.update(mpl.rcParamsDefault)
    mpl.rcParams.update({
        # Typographie : corps 7 pt à la taille finale, jamais sous 6 pt.
        "font.family": "serif",
        "font.size": 7.0,
        "axes.titlesize": 7.5,
        "axes.labelsize": 7.0,
        "xtick.labelsize": 6.5,
        "ytick.labelsize": 6.5,
        "legend.fontsize": 6.5,
        "axes.formatter.use_mathtext": True,
        "axes.unicode_minus": True,
        "text.color": INK,
        # Axes : deux épines, traits fins, quadrillage discret sous les données.
        "axes.edgecolor": INK,
        "axes.labelcolor": INK,
        "axes.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "axes.titlelocation": "left",
        "axes.titlepad": 4.0,
        "axes.labelpad": 2.5,
        "axes.prop_cycle": mpl.cycler(color=PALETTE),
        "grid.color": GRID,
        "grid.linewidth": 0.45,
        "grid.linestyle": "-",
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.color": INK,
        "ytick.color": INK,
        "xtick.major.size": 2.8,
        "ytick.major.size": 2.8,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.minor.size": 1.6,
        "ytick.minor.size": 1.6,
        "xtick.minor.width": 0.45,
        "ytick.minor.width": 0.45,
        "xtick.major.pad": 2.0,
        "ytick.major.pad": 2.0,
        # Marques : lignes 1,2 pt, tirets courts restant lisibles à 7 cm.
        "lines.linewidth": 1.2,
        "lines.markersize": 3.5,
        "lines.dashed_pattern": (3.2, 1.6),
        "lines.dashdot_pattern": (4.0, 1.4, 1.0, 1.4),
        "lines.dotted_pattern": (1.0, 1.4),
        "lines.solid_capstyle": "butt",
        "lines.dash_capstyle": "butt",
        "patch.linewidth": 0.5,
        "scatter.edgecolors": "none",
        # Légendes : placement automatique, cadre léger qui masque la grille.
        "legend.loc": "best",
        "legend.frameon": True,
        "legend.fancybox": False,
        "legend.framealpha": 0.92,
        "legend.edgecolor": "#C8C8C8",
        "legend.facecolor": "white",
        "legend.borderpad": 0.35,
        "legend.borderaxespad": 0.5,
        "legend.labelspacing": 0.28,
        "legend.handlelength": 2.2,
        "legend.handleheight": 0.6,
        "legend.handletextpad": 0.5,
        "legend.columnspacing": 1.0,
        "legend.numpoints": 1,
        "legend.scatterpoints": 1,
        # Mise en page et export.
        "figure.constrained_layout.use": True,
        "figure.constrained_layout.h_pad": 0.02,
        "figure.constrained_layout.w_pad": 0.03,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.015,
        "savefig.dpi": 600,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "pdf.compression": 9,
    })
    mpl.rcParams.update(_FONT_PRESETS[preset])


def subplots(nrows: int = 1, ncols: int = 1, *, width: float = DOUBLE_COLUMN,
             height: float | None = None, **kwargs):
    """Crée une figure dimensionnée à sa taille d'impression finale."""
    import matplotlib.pyplot as plt

    if height is None:
        height = 1.8 * nrows if width >= DOUBLE_COLUMN else 1.9 * nrows
    return plt.subplots(nrows, ncols, figsize=(width, height), **kwargs)


def panel_title(axis, letter: str, text: str) -> None:
    """Titre de panneau aligné à gauche : lettre en gras, puis intitulé court."""
    axis.set_title(rf"$\mathbf{{({letter})}}$ {text}")


def ecdf(axis, values, **kwargs):
    """Trace la fonction de répartition empirique F(x) = P(X <= x).

    Les valeurs identiques sont regroupées : la courbe est exacte mais le PDF
    ne contient qu'un sommet par valeur distincte.
    """
    ordered, counts = np.unique(np.asarray(values, dtype=float), return_counts=True)
    fractions = np.cumsum(counts) / counts.sum()
    xs = np.concatenate(([ordered[0]], ordered))
    ys = np.concatenate(([0.0], fractions))
    return axis.step(xs, ys, where="post", **kwargs)


def ccdf(axis, values, **kwargs):
    """Trace la fonction de survie P(X >= x), adaptée à un axe y logarithmique.

    Le dernier point vaut 1/n : la valeur maximale reste visible au lieu de
    tomber à zéro hors de l'échelle.
    """
    ordered, counts = np.unique(np.asarray(values, dtype=float), return_counts=True)
    at_least = (counts.sum() - np.concatenate(([0], np.cumsum(counts)[:-1]))) / counts.sum()
    return axis.step(ordered, at_least, where="pre", **kwargs)


def strip(axis, x: float, values, *, width: float = 0.14, seed: int = 0, **kwargs):
    """Observations individuelles d'une catégorie, décalées horizontalement.

    Le décalage est pseudo-aléatoire mais déterministe : la figure est identique
    d'une exécution à l'autre.
    """
    values = np.asarray(values, dtype=float)
    offsets = np.random.default_rng(seed).uniform(-width, width, size=values.size)
    style = {"s": 9, "alpha": 0.7, "linewidths": 0, "zorder": 3}
    style.update(kwargs)
    return axis.scatter(x + offsets, values, **style)


def interval(axis, x: float, center: float, low: float, high: float, **kwargs):
    """Statistique résumée et son intervalle : point à l'encre, barre à coiffes courtes."""
    style = {"fmt": kwargs.pop("marker", "o"), "color": INK, "markersize": 3.2, "linewidth": 0.9,
             "capsize": 2.0, "capthick": 0.9, "zorder": 4}
    style.update(kwargs)
    return axis.errorbar([x], [center], yerr=[[center - low], [high - center]], **style)


def fixed_ticks(axis, which: str, values, digits: int | None = None) -> None:
    """Graduations choisies explicitement, écrites au format français.

    Sans ``digits``, chaque valeur garde ses seuls chiffres utiles (0,25 ; 1 ; 4 096).
    """
    from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator

    def label(value, _):
        if digits is not None:
            return french_number(value, digits)
        if float(value).is_integer():
            return french_number(value, 0)
        return f"{value:g}".replace(".", ",")

    target = axis.xaxis if which == "x" else axis.yaxis
    target.set_major_locator(FixedLocator(list(values)))
    target.set_major_formatter(FuncFormatter(label))
    target.set_minor_locator(NullLocator())


def french_ticks(axis, which: str, digits: int | None = None) -> None:
    """Conserve les graduations automatiques mais les écrit avec une virgule décimale."""
    from matplotlib.ticker import FuncFormatter

    def label(value, _):
        if digits is not None:
            return french_number(value, digits)
        return f"{value:g}".replace(".", ",").replace("-", "−")

    (axis.xaxis if which == "x" else axis.yaxis).set_major_formatter(FuncFormatter(label))


def reference_style(**kwargs) -> dict:
    """Style commun des repères (diagonale, cible, seuil) : gris et pointillé."""
    style = {"color": REFERENCE, "linestyle": ":", "linewidth": 0.8, "zorder": 1}
    style.update(kwargs)
    return style


def log_axis(axis, which: str = "x") -> None:
    """Axe logarithmique en base 10 avec graduations mineures discrètes.

    Le formateur mineur par défaut de matplotlib est conservé : il n'étiquette
    les graduations 2, 3, 5... que si l'axe couvre environ une décennie ou moins.
    """
    from matplotlib.ticker import LogLocator

    target = axis.xaxis if which == "x" else axis.yaxis
    (axis.set_xscale if which == "x" else axis.set_yscale)("log")
    target.set_major_locator(LogLocator(base=10, numticks=12))
    target.set_minor_locator(LogLocator(base=10, subs=np.arange(2, 10), numticks=12))


def decade_limits(*groups, pad: float = 0.5) -> tuple[float, float]:
    """Bornes logarithmiques arrondies au multiple de ``pad`` décade le plus proche."""
    data = np.concatenate([np.asarray(group, dtype=float) for group in groups])
    lower = math.floor(math.log10(data.min()) / pad) * pad
    upper = math.ceil(math.log10(data.max()) / pad) * pad
    return 10 ** lower, 10 ** upper


def significant(value: float, digits: int = 2) -> float:
    """Arrondit à ``digits`` chiffres significatifs pour ne pas afficher de fausse précision."""
    if value == 0:
        return 0.0
    return round(value, digits - 1 - math.floor(math.log10(abs(value))))


def duration_ns(value: float) -> str:
    """Durée donnée en ns, écrite dans l'unité où elle a au plus trois chiffres entiers."""
    for scale, unit in ((1e9, "s"), (1e6, "ms"), (1e3, "µs")):
        if value >= scale:
            return f"{french_number(value / scale, 2)} {unit}"
    return f"{french_number(value, 0)} ns"


def french_number(value: float, digits: int = 0) -> str:
    """Nombre au format français : virgule décimale, espace fine insécable."""
    text = f"{value:,.{digits}f}"
    return text.replace(",", " ").replace(".", ",")


def save(figure, path: Path | str) -> None:
    """Exporte le PDF vectoriel (figure de l'article) et un PNG à 600 dpi.

    Les métadonnées de date sont retirées pour que deux exécutions sur les
    mêmes données produisent le même PDF.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path.with_suffix(".pdf"), metadata={"CreationDate": None})
    figure.savefig(path.with_suffix(".png"), metadata={"Software": None})


def warn(message: str) -> None:
    print(f"figstyle: {message}", file=sys.stderr)
