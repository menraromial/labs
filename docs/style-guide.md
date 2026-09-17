# Guide de rédaction et de typographie

## Typographie

- Le caractère Unicode U+2014 est interdit dans le dépôt et dans les réponses.
- Utiliser le tiret simple `-` quand une séparation est nécessaire.
- Employer des titres courts et des libellés avec unités explicites.
- Nombres au format français : virgule décimale (0,98), espace entre groupes de
  trois chiffres (50 000).

## Structure d'un compte rendu

Chaque `experiments/NN-nom/README.md` suit les 12 parties du cahier des charges,
dans cet ordre et avec ces numéros :

1. Question et prérequis (paragraphe `**Question :**`, sans formule).
2. Notions nécessaires, terminées par une sous-partie **Notations**.
3. Modèle de coût et prédictions, écrits avant la campagne (avec la transparence
   sur tout résultat entrevu).
4. Code et parties importantes.
5. Commandes.
6. Vérification de correction, indépendante de la mesure.
7. Protocole de la campagne.
8. Données brutes.
9. Figures.
10. Résultats observés et interprétation.
11. Limites et expériences suivantes.
12. Compréhension et prolongement.

## Notations : rien n'est employé avant d'être défini

- La sous-partie **Notations** de la section 2 est un tableau qui définit, avant la
  première prédiction, **chaque** variante mesurée et **chaque** symbole employé
  dans le document : nom, signification en mots, unité.
- Une variante mesurée garde le nom qu'elle porte dans les données, écrit en code
  (`rand_read_cold`), et sa définition dit ce que le programme exécute.
- Un symbole n'a qu'un sens dans un document. Les durées s'écrivent $t$, les
  coûts fixes et coûts par unité reçoivent une lettre définie une fois (par
  exemple $H$ et $C$), les rapports s'écrivent comme des quotients de ces
  symboles.
- Un terme technique nouveau est défini en français, avec son équivalent anglais
  en italique, et ajouté au glossaire.

## Équations

Le site rend les formules avec KaTeX.

- Formule en ligne : `$t_{\text{CPU}}$` ; formule en bloc : `$$ ... $$` sur des
  lignes séparées.
- Un modèle de coût, un rapport ou une conversion est toujours écrit en
  formule, jamais en code.
- Virgule décimale protégée : `0{,}98` ; espace fine entre milliers : `13\,000`.
- Mots dans une formule : `\text{...}`. Unités : `\ \text{ms}`, `\mu\text{s}`.
- Dans un tableau, pas de barre verticale `|` dans une formule : utiliser
  `\lvert x \rvert`.
- Un `$` isolé dans le texte courant s'écrit dans du code (`` `$HOME` ``).

## Prose

- Phrases complètes. Une liste sert à énumérer des éléments parallèles, pas à
  remplacer un raisonnement.
- Chaque résultat donne sa valeur, son intervalle ou son étendue, et la
  prédiction qu'il confirme ou réfute, écrite telle quelle.
- Distinguer explicitement ce qui est garanti, ce qui dépend de la machine, ce qui
  est observé et ce qui reste une hypothèse.
- Pas de chiffre sans source : tout nombre vient des données, d'un calcul
  explicite à partir d'elles, ou d'une prédiction datée.

## Figures scientifiques

Les règles des figures sont regroupées à la racine du dépôt, dans
[`STYLE_FIGURES.md`](../STYLE_FIGURES.md), et appliquées par
[`tools/figstyle.py`](../tools/figstyle.py). Les libellés des figures emploient les
mêmes noms et symboles que le compte rendu.
