# Règles de style des figures

Ces règles visent le niveau attendu dans les conférences de rang A/A* en
systèmes, performance et distribué (OSDI, SOSP, NSDI, EuroSys, USENIX ATC, FAST,
ASPLOS, SIGCOMM, PODC). Elles s'appliquent à **toutes** les figures du dépôt.

Le module [`tools/figstyle.py`](tools/figstyle.py) applique ces règles. Ce
fichier fait référence : si une règle change, le module change dans le même
commit.

```python
import figstyle                            # tools/ ajouté au sys.path
figstyle.use("times")                      # "acm" pour un gabarit ACM
fig, axes = figstyle.subplots(2, 2, height=3.15)
figstyle.ecdf(axes[0, 0], valeurs, color=figstyle.PALETTE[0], label="Lecture isolée")
axes[0, 0].legend()                        # loc="best" est imposé par le style
figstyle.panel_title(axes[0, 0], "a", "Lecture d'horloge : corps")
figstyle.save(fig, "figures/campagne.pdf") # PDF vectoriel + PNG 600 dpi
```

Exemple de référence : [`experiments/01-time/analyze.py`](experiments/01-time/analyze.py).

---

## 1. Dimensions : dessiner à la taille d'impression

| Gabarit | Une colonne | Pleine largeur |
|---|---|---|
| ACM `acmart` (sigconf), USENIX | 3,33 in (8,5 cm) | 7,0 in (17,8 cm) |
| IEEE `IEEEtran` | 3,5 in (8,9 cm) | 7,16 in (18,2 cm) |

- Créer la figure **à sa largeur finale** (`figstyle.SINGLE_COLUMN`,
  `figstyle.DOUBLE_COLUMN`). Une figure réduite par LaTeX rétrécit aussi ses
  polices et ses traits : c'est la première cause d'aspect amateur.
- L'inclure sans mise à l'échelle : `\includegraphics{figures/x.pdf}`, ou
  `width=\textwidth` uniquement si elle a été créée à cette largeur.
- Hauteur indicative : 1,8 in par rangée en pleine largeur, 1,9 in en colonne.
- Une rangée de quatre panneaux n'est acceptable que si chaque légende trouve
  une place libre. Sinon, passer en grille 2x2 plutôt que de masquer des données.

## 2. Typographie

- Police à empattements identique au texte de l'article :
  - préréglage `times` (USENIX, IEEE) : STIX Two Text, mathématiques STIX ;
  - préréglage `acm` (ACM) : Linux Libertine.
- Tailles à l'impression : corps et axes 7 pt, graduations et légendes 6,5 pt,
  titres de panneau 7,5 pt, annotations 6 pt. **Jamais moins de 6 pt.**
- Aucun titre général dans l'image : il appartient à la légende LaTeX
  (`\caption`). Chaque panneau porte un titre court aligné à gauche,
  `(a) Intitulé`, la lettre en gras (`figstyle.panel_title`).
- Libellés d'axe en minuscules sauf initiale, avec unité entre parenthèses :
  `Durée par lecture (ns)`. Pas de « échelle log » dans le libellé : les
  graduations en puissances de dix l'indiquent.
- Symboles mathématiques en mode mathtext (`r"$P(X \geq x)$"`, `$\approx$`) :
  certains glyphes (≥, ≈) manquent dans les polices de texte.
- Nombres au format français dans le texte et sur les axes : virgule décimale,
  espace fine pour les milliers (`figstyle.french_number`, graduations avec
  `figstyle.fixed_ticks` ou `figstyle.french_ticks`), durées dans l'unité adaptée
  (`figstyle.duration_ns`). Arrondir à la précision réellement défendable
  (`figstyle.significant`) : « 3 700 », pas « 3 744 ».
- Caractère U+2014 (tiret cadratin) interdit, comme partout dans le dépôt.

## 3. Couleur

Palette catégorielle validée (Okabe-Ito, violet assombri pour le contraste),
**dans cet ordre fixe** :

| Rang | Hex | Nom |
|---|---|---|
| 1 | `#0072B2` | bleu |
| 2 | `#D55E00` | vermillon |
| 3 | `#009E73` | vert bleuté |
| 4 | `#882E72` | violet |

Validation (outil `validate_palette.js`, fond clair, toutes les paires) :
luminance et chroma dans les bornes, séparation daltonisme ΔE ≥ 8,6,
vision normale ΔE ≥ 18,7, contraste ≥ 3:1 sur blanc. Toute nouvelle couleur
doit repasser ce contrôle.

- **La couleur suit l'entité, pas son rang.** Une entité (ex. « Attente »)
  garde la même couleur dans tous les panneaux d'une figure, et idéalement dans
  toutes les figures de l'article.
- Deux entités différentes ne partagent jamais une couleur dans une figure.
- Au-delà de quatre séries : regrouper, facetter (petits multiples) ou changer
  de forme. Ne jamais générer une cinquième teinte.
- Repères (diagonale, cible, seuil) en gris `#8A8A8A`, pointillés.
- Textes, annotations et légendes en encre neutre (`#1A1A1A` ou `#5A5A5A`),
  jamais dans la couleur d'une série.
- Magnitude continue : une seule teinte, du clair au foncé. Écart à une
  référence : deux teintes et un gris neutre au milieu. Jamais d'arc-en-ciel
  (`jet`, `rainbow`).

## 4. Encodage secondaire

La figure doit rester lisible **imprimée en niveaux de gris** et pour un
lecteur daltonien, sans compter sur la couleur.

- Une **métrique** a un style de ligne constant : temps écoulé en trait plein,
  temps CPU en tirets (ordre général : `-`, `--`, `-.`, `:`).
- Une **entité** en nuage de points a un marqueur constant (`o`, `s`, `^`, `D`,
  selon son rang dans la palette).
- Vérifier en convertissant le PNG en niveaux de gris avant de valider.

## 5. Marques

- Lignes de données : 1,2 pt ; repères : 0,8 pt pointillé.
- Distributions : fonctions en escalier (`figstyle.ecdf`, `figstyle.ccdf`),
  jamais lissées ni interpolées.
- Nuages de points : marqueurs d'environ 3,5 pt (`s=11`), `alpha=0.7`, sans
  contour, pour que les superpositions restent visibles.
- Pas de marqueur sur une courbe dense ; un marqueur isolé sert à désigner un
  point commenté (ex. le maximum).
- Catégories comparées (protocoles, affinités) : chaque unité indépendante est
  un point décalé horizontalement de façon déterministe (`figstyle.strip`), et
  la statistique résumée est un point à l'encre avec son intervalle, placé à
  droite des points (`figstyle.interval`). Nommer l'intervalle dans la légende
  (« Médiane, IC 95 % »).
- Rapports (A/B, accélération) : axe logarithmique, pour que 0,5 et 2 soient à
  égale distance de 1, avec la valeur de référence en repère gris.
- Aucun effet : pas d'ombre, de dégradé, de 3D, de remplissage décoratif.

## 6. Axes et grille

- Deux épines seulement (gauche et bas), 0,6 pt ; graduations vers l'extérieur.
- Quadrillage majeur gris très clair (`#E4E4E4`, 0,45 pt), sous les données.
- Échelle logarithmique en base 10 (`figstyle.log_axis`) dès que les données
  couvrent plus d'environ deux décennies ; bornes arrondies à la décennie
  (`figstyle.decade_limits`).
- Une probabilité va de 0 à 1 (marge supérieure de 2 %) sur un axe linéaire,
  ou jusqu'à 1/n sur un axe logarithmique de survie.
- **Un seul axe y par panneau.** Deux grandeurs d'échelles différentes vont dans
  deux panneaux.
- Rogner un axe est permis pour montrer le corps d'une distribution **à deux
  conditions** : annoter le nombre et la part des valeurs hors cadre, et
  renvoyer au panneau qui les montre (ex. « 16 valeurs > 50 ns (0,03 %),
  voir (b) »).

## 7. Légendes

- **Toujours `loc="best"`** (imposé par `figstyle.use`) et toujours à
  l'intérieur des axes. Appeler `axis.legend()` sans argument de position.
- Ajouter les annotations **avant** la sauvegarde : le placement automatique
  évite les courbes, les nuages de points et les textes déjà présents.
- Cadre blanc à 92 % d'opacité, bord gris clair de 0,5 pt, coins droits. Le
  cadre masque la grille, pas des données.
- Si `best` ne trouve aucune place libre, la légende recouvre une courbe :
  c'est un défaut de mise en page. Raccourcir les libellés ou changer la
  disposition (ex. 1x4 vers 2x2) ; ne jamais accepter le recouvrement.
- Libellés courts, forme « Entité, métrique » (`Calcul, CPU`), dans l'ordre du
  tracé. Les repères utiles à la lecture y figurent (`Écoulé = CPU`).
- Une légende dès deux séries ; aucune pour une série unique (le libellé d'axe
  ou le titre la nomme).
- Petits multiples dont tous les panneaux d'une rangée tracent les mêmes séries
  avec les mêmes couleurs : une seule légende, dans le premier panneau de la
  rangée. Si les libellés portent une information propre au panneau (pente,
  valeur ajustée), chaque panneau garde sa légende.
- Un intitulé commun aux entrées va dans le titre de la légende
  (`legend(title="Niveau : pente ; boucle")`), pas répété dans chaque libellé :
  des libellés courts laissent `best` trouver une place libre.

## 8. Annotations

- Sélectives : un maximum, un rapport, un nombre de valeurs rognées. Jamais une
  valeur sur chaque point.
- 6 pt, gris `#5A5A5A`, placées près de l'objet désigné, sans chevauchement.
- Une flèche fine (0,6 pt) peut matérialiser un écart qui porte le message
  (ex. écart vertical à la diagonale écoulé = CPU).
- Toute valeur annotée est calculée depuis les données brutes par le script,
  jamais recopiée à la main.

## 9. Choisir la forme

| Question | Forme recommandée |
|---|---|
| Distribution d'une latence ou d'une durée | ECDF |
| Traîne, valeurs rares | fonction de survie P(X ≥ x) en log-log |
| Deux mesures appariées (CPU et écoulé) | nuage de points avec diagonale y = x |
| Passage à l'échelle | courbe par variante, marqueurs aux points mesurés, dispersion en bande ou barres |
| Comparaison de quelques conditions | points avec intervalles, pas de barres de moyennes |

- Montrer toutes les observations ou une distribution ; ne jamais réduire à une
  moyenne sans dispersion.
- Ne jamais supprimer une valeur atypique pour embellir.
- Pas de percentile extrême sur un échantillon trop petit (pas de p99 sur 50
  observations).
- Interdits : camemberts, barres empilées pour des distributions, doubles axes y,
  histogrammes dont le choix de classes change la conclusion.

## 10. Export

- PDF vectoriel pour l'article, polices TrueType incorporées en sous-ensemble
  (`pdf.fonttype = 42`) : les vérificateurs de soumission, IEEE PDF eXpress
  notamment, signalent les polices Type 3 produites par défaut par matplotlib.
- Lorsqu'une police existe en `.ttf` et en `.otf`, la version TrueType est
  imposée (`figstyle.use` écarte le doublon OpenType) : une police CFF déclarée
  TrueType produit l'avertissement « Mismatch between font type and embedded
  font file ». Le préréglage `acm` n'a ici que des fichiers `.otf` : contrôler
  son PDF avec `pdffonts` avant soumission.
- PNG à 600 dpi pour les documents et les aperçus.
- Métadonnées de date retirées : mêmes données, même PDF.
- Les figures sont toujours régénérées par le script depuis les données brutes,
  jamais retouchées à la main.

## 11. Liste de contrôle avant de valider une figure

- [ ] Créée à la largeur finale, incluse sans mise à l'échelle.
- [ ] Aucun texte sous 6 pt ; unités présentes sur chaque axe.
- [ ] Couleur constante par entité ; palette validée ; repères en gris.
- [ ] Lisible en niveaux de gris (styles de ligne, marqueurs).
- [ ] Chaque légende en `best`, sans recouvrir de données.
- [ ] Aucune annotation qui chevauche une courbe, un axe ou une autre annotation.
- [ ] Valeurs rognées annotées et montrées ailleurs ; aucune donnée supprimée.
- [ ] `pdffonts figure.pdf` : toutes les polices `emb yes`, aucune `Type 3`,
      aucun avertissement « Mismatch ».
- [ ] Figure regardée à 100 % dans le PDF, pas seulement dans le PNG.
