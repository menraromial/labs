# A2 - Réparer un microbenchmark naïf

## 1. Question et prérequis

**Question :** un microbenchmark naïf peut-il conclure qu'une fonction est plus
rapide qu'elle-même, ou que doubler le travail ne coûte presque rien ? Quelles
corrections (lots, répétitions, ordre, échauffement, exécutions indépendantes)
rendent la conclusion défendable sur cette machine ?

Prérequis : le projet [A1](../01-time/README.md), en particulier la différence
entre résolution, coût de lecture et temps écoulé, et le coût médian d'environ
28 ns mesuré pour deux lectures consécutives de `CLOCK_MONOTONIC`.

## 2. Notions nécessaires

Termes nouveaux, avec leur équivalent anglais :

- **Microbenchmark** (*microbenchmark*) : mesure d'une opération très courte,
  isolée de l'application. Intuitivement, c'est chronométrer un seul geste au
  lieu d'une journée de travail : l'erreur du chronomètre pèse beaucoup plus.
- **Lot** (*batch*) : plusieurs opérations entre deux lectures d'horloge. Le coût
  fixe du chronométrage est partagé entre elles.
- **Répétition** (*repetition*) : nouvelle mesure dans le même processus.
- **Exécution indépendante** (*independent run*) : nouveau processus. Il peut
  être placé sur un autre cœur, rencontrer une autre fréquence ou une autre
  disposition mémoire ; des répétitions dans un seul processus ne voient pas
  cette variabilité.
- **Échauffement** (*warm-up*) : période initiale pendant laquelle les coûts
  peuvent différer du régime établi (fréquence du CPU qui monte, caches et
  prédicteurs encore vides, pages pas encore chargées). Sa durée se **mesure** ;
  elle ne se suppose pas.
- **Biais d'ordre** (*order bias*) : écart systématique dû à la position d'une
  variante dans la séquence de mesure, et non à la variante elle-même.
- **Entrelacement** (*interleaving*) : alterner les variantes dans chaque tour,
  dans un ordre tiré au hasard, pour que la dérive de la machine touche toutes les
  variantes de la même façon.
- **Contrôle négatif, test A/A** (*negative control*, *A/A test*) : comparer une
  variante à elle-même. Le rapport vrai vaut 1 ; tout écart observé mesure
  l'erreur du protocole.
- **Contrôle positif** (*positive control*) : comparer à une variante dont
  l'écart est connu par construction. Il vérifie que le protocole détecte une
  vraie différence.
- **Intervalle de confiance bootstrap** (*bootstrap confidence interval*) :
  intervalle obtenu en rééchantillonnant les unités indépendantes (ici les
  processus) avec remise, puis en recalculant la statistique.
- **Affinité CPU** (*CPU affinity*) : ensemble des CPU logiques sur lesquels le
  noyau peut exécuter un processus. `taskset -c 11 programme` le restreint au
  CPU 11.
- **Cœurs hybrides** (*hybrid cores*) : processeur combinant cœurs performants
  (*P-cores*) et cœurs efficaces (*E-cores*), de microarchitectures et fréquences
  maximales différentes.

Ce qui est **garanti** : `CLOCK_MONOTONIC` ne recule pas ; `A` et `A_bis`
appellent la même fonction machine ; `B` fait exactement deux fois plus d'appels
à `tiny_work` par opération ; `taskset` restreint l'affinité (vérifié dans les
données). Ce qui **dépend de la machine** : coût d'une lecture d'horloge, coût de
`tiny_work`, montée en fréquence (ici `intel_pstate`, gouverneur `powersave`,
préférence énergétique `power`), placement par l'ordonnanceur.

## 3. Prédictions et ordre de grandeur, écrits avant la campagne

**Transparence :** avant d'écrire ces lignes, nous avions vu trois exécutions
rapides d'une version antérieure du programme (plateau d'environ 6 ns par
opération, 44 ns pour un lot de 1) et deux essais de mise au point du programme
actuel. Les prédictions ci-dessous en tiennent compte ; elles ne sont donc pas
aveugles sur l'ordre de grandeur.

Modèle : `T_lot(N) = H + N × C`, donc `T_lot(N) / N = C + H / N`, où `H` regroupe
les lectures d'horloge, l'appel indirect et l'entrée dans la boucle, et `C` le
coût d'une opération dans ce programme.

Calcul d'ordre de grandeur, avec `H ≈ 38 ns` et `C ≈ 6 ns` :

- lot de 1 : coût apparent `≈ 44 ns`, soit environ 7 fois le coût du travail ;
- lot de 20 000 : `H / N ≈ 0,002 ns`, négligeable ;
- rapport naïf `B/A ≈ (H + 2C) / (H + C) ≈ 50 / 44 ≈ 1,14`, alors que `B` fait
  deux fois plus d'appels.

Prédictions :

1. **Amortissement :** coût par opération décroissant approximativement en
   `1/N`, plateau atteint vers quelques centaines d'opérations ; `H` estimé entre
   25 et 50 ns, `C` entre 3 et 10 ns.
2. **Protocole naïf (1 opération, ordre fixe A, A_bis, B) :** `B/A` médian
   entre 1,05 et 1,4, donc une forte sous-estimation de l'écart réel ; `A_bis/A`
   très dispersé entre processus, et inférieur à 1 dans la majorité d'entre eux,
   car `A`, mesuré en premier, paierait les effets de démarrage.
3. **Lot unique (20 000 opérations, ordre fixe) :** `B/A` proche de 2 mais encore
   biaisé ; `A_bis/A` inférieur à 1 dans la majorité des processus (montée en
   fréquence pendant le premier lot).
4. **Lots entrelacés (100 tours, ordre aléatoire, 10 tours d'échauffement
   déclarés) :** `A_bis/A` médian entre 0,98 et 1,02 avec un intervalle contenant
   1 ; `B/A` entre 1,8 et 2,05 (la boucle est partagée par deux appels dans `B`,
   ce qui peut placer le rapport légèrement sous 2).
5. **Échauffement :** premiers tours plus lents que le régime établi, retour vers
   la médiane en quelques millisecondes ; 10 tours suffiraient.
6. **Cœurs :** coût par opération `P < E < LP-E`. Le seul rapport des fréquences
   maximales (5,0 ; 3,8 ; 2,5 GHz) suggérerait `E/P ≈ 1,3` et `LP-E/P ≈ 2`, mais
   les microarchitectures diffèrent : c'est une hypothèse, pas un calcul.
7. **Dispersion :** sans affinité, la dispersion entre processus dépasse la
   dispersion entre répétitions d'un même processus, parce que les processus
   tombent sur des types de cœurs différents ; épinglés, elle diminue.

### 3 bis. Contrôle exploratoire, décidé après la première campagne

La première campagne (archivée dans `data/campaign-v1`) a produit deux
observations inattendues. Elles ne font pas partie des prédictions ci-dessus et
les contrôles suivants sont donc **exploratoires** :

- en naïf, le premier échantillon du processus (`A`) coûtait environ 160 ns,
  contre 37 ns pour `A_bis`, et `B` 72 ns au lieu d'environ 42 ns attendus ;
- le « ralentissement initial » des lots entrelacés valait exactement le rapport
  des coûts sur cœur E et sur cœur P, et 26 processus sur 30 commençaient sur un
  cœur E.

**Hypothèse H1, premier passage à froid :** la première exécution d'un chemin de
code dans un processus coûte plus cher (prédicteurs de branchement vides,
instructions et traductions d'adresses absentes des caches, pages du vDSO pas
encore accédées). `B` est la première exécution de `run_double`, `A` la première
lecture d'horloge et le premier appel de `run_single`.

Contrôle : protocole naïf, 30 processus par condition, avec un amorçage non
chronométré juste avant la première mesure :

| Condition | Amorçage | Si H1 est vraie |
|---|---|---|
| `none` | aucun | reproduit `A` ≫ `A_bis` et `B` > `A_bis` + quelques ns |
| `clock` | une lecture d'horloge | `A` diminue si la première lecture d'horloge compte ; `B` inchangé |
| `code` | un appel direct de `run_single` et de `run_double` | `B` redescend vers `A_bis` + `C` ; `A` diminue si le code compte |
| `full` | une mesure complète de chaque variante, jetée | `A ≈ A_bis` et `B/A ≈ (H + 2C) / (H + C) ≈ 1,1 à 1,2` |

Nous ne savons pas prédire lequel, de la lecture d'horloge ou du code, domine :
les deux conditions intermédiaires servent à le départager.

**Hypothèse H2, placement par l'ordonnanceur :** un nouveau processus démarre
souvent sur un cœur E et n'est déplacé vers un cœur P qu'après quelques
millisecondes de calcul. Elle sera évaluée sans nouvelle mesure, à partir du CPU
de chaque échantillon (`sched_getcpu`), dans la campagne rejouée.

**Réplication :** pour que toutes les données comparées proviennent du même
binaire, la campagne principale est rejouée à l'identique avec le programme final
(qui ajoute l'option `--prime` et ne laisse plus le compilateur intégrer `measure`
à son appelant). La campagne `v1` sert de réplication indépendante.

## 4. Code

- [`src/microbench.c`](src/microbench.c) : travail mesuré, trois modes de
  mesure, plan construit avant la première mesure, résultats gardés en mémoire
  puis écrits après la dernière mesure.
- [`prepare.py`](prepare.py) : topologie des cœurs et plan complet des processus,
  dans un ordre tiré au hasard avec la graine `20260916`.
- [`run.sh`](run.sh) : un processus indépendant par ligne du plan, épinglé avec
  `taskset` si le plan le demande.
- [`verify.py`](verify.py) : complétude du plan, épinglage effectif et, pour
  `make check`, rejeu exact des calculs en Python.
- [`analyze.py`](analyze.py) : résumés, intervalles bootstrap et figures suivant
  [`STYLE_FIGURES.md`](../../STYLE_FIGURES.md).

Parties importantes du programme :

- `tiny_work` est marquée `noinline` et chaque résultat devient l'entrée de
  l'appel suivant : le compilateur ne peut ni supprimer ni paralléliser les
  opérations. Le désassemblage (`objdump -d build/microbench`) montre bien un
  `call tiny_work` par itération.
- `A` et `A_bis` passent par la même entrée de table et le même pointeur de
  fonction ; `B` utilise `run_double`, deux appels par itération.
- L'intervalle chronométré contient les deux lectures d'horloge, l'appel indirect
  et la boucle. `sched_getcpu` est appelé juste avant et juste après, hors
  intervalle, pour savoir sur quel CPU l'échantillon a été pris.
- Aucune écriture de fichier n'a lieu pendant la phase de mesure.

## 5. Commandes

```sh
make check      # correction uniquement, aucune conclusion de performance
make quick      # validation de la chaîne, quelques secondes
make campaign   # campagne documentée ; refuse d'écraser data/campaign
make prime      # contrôle exploratoire d'amorçage (section 3 bis)
make analyze    # recalcule résumés et figures depuis les données conservées
```

Compilation exacte : `cc -O2 -std=c17 -Wall -Wextra -Wpedantic src/microbench.c -o build/microbench`.

## 6. Vérification de correction, indépendante de la mesure

- `--self-test` : `tiny_work` égale une formulation de référence ;
  `run_single(s, n)` égale `n` applications de la référence ; `run_double(s, n)`
  égale `run_single(s, 2n)` ; le mélange produit bien des permutations.
- `verify.py --replay` réimplémente le calcul en Python et vérifie, ligne par
  ligne, que le résultat écrit correspond exactement à `ops × calls_per_op`
  appels depuis la graine. Le travail chronométré a donc réellement eu lieu.
- `verify.py` vérifie aussi que chaque processus du plan a produit toutes ses
  lignes et que les processus épinglés n'avaient qu'un CPU autorisé, sur lequel
  tous leurs échantillons ont été pris.

Aucune de ces vérifications n'impose de seuil de performance.

## 7. Protocole de la campagne

Plan de 155 processus, exécutés un par un dans un ordre aléatoire fixé :

| Partie | Protocole | Processus | Contenu d'un processus |
|---|---|---:|---|
| Amortissement | `amortization` | 20 | 40 répétitions de chaque taille 1, 2, 4... 32 768, ordre mélangé, 100 000 opérations préalables |
| Réparation | `naive` | 30 | 1 opération de A, puis A_bis, puis B ; aucune répétition |
| Réparation | `batched` | 30 | 20 000 opérations de A, puis A_bis, puis B ; aucune répétition |
| Réparation | `interleaved` | 30 | 100 tours de 20 000 opérations, ordre des 3 variantes tiré à chaque tour |
| Affinité | `interleaved` épinglé | 15 × 3 | idem, sur le CPU 11 (P), 19 (E) ou 21 (LP-E) |

- Unité statistique : le **processus**. Pour `interleaved`, le coût d'une
  variante dans un processus est la médiane de ses 90 tours hors échauffement ;
  le rapport du processus est le rapport de ces médianes.
- Les 10 premiers tours sont déclarés échauffement **avant** la mesure. Ils sont
  conservés dans les données et tracés pour vérifier ce choix.
- Résumé entre processus : médiane et intervalle bootstrap percentile à 95 %
  (10 000 rééchantillonnages des processus, graine fixe).
- Critère de conclusion trompeuse, fixé à l'avance : `|A_bis/A - 1| > 5 %`.
- Le modèle `C + H/N` est ajusté par moindres carrés relatifs sur les médianes
  entre processus ; l'intervalle de `H` et `C` vient d'un bootstrap des processus.
- Observables de remplacement des compteurs matériels, indisponibles avec
  `perf_event_paranoid=4` : CPU logique de chaque échantillon (`sched_getcpu`),
  défauts de page et changements de contexte du processus (`getrusage`).
- GCC `-O2`, C17, aucun réglage global de la machine, aucune modification du
  gouverneur de fréquence. L'environnement est consigné dans
  `data/environment-campaign.txt`, la topologie dans `data/campaign/topology.csv`.

## 8. Données brutes

| Dossier | Contenu | Programme |
|---|---|---|
| [`data/campaign/`](data/campaign/) | campagne de référence, 155 processus | version finale |
| [`data/prime/`](data/prime/) | contrôle d'amorçage, 120 processus | version finale |
| [`data/campaign-v1/`](data/campaign-v1/) | première campagne, même plan, réplication | version sans `--prime` |

Chaque dossier contient `plan.csv` (écrit avant la mesure), `topology.csv`, un
fichier `run-NNN.csv` par processus (une ligne par échantillon, avec les CPU
avant et après) et `run-NNN-meta.csv` (défauts de page et changements de
contexte pendant la mesure). Environnements : `data/environment-*.txt`, avec
les empreintes SHA-256 du source et du binaire pour les données de la version
finale. Aucune observation n'a été retirée.

Résumés calculés : `reports/campaign-*.csv` (référence et amorçage) et
`reports/campaign-v1-*.csv` (réplication).

## 9. Figures

- [`figures/campaign-amortization.pdf`](figures/campaign-amortization.pdf) :
  (a) coût apparent selon la taille du lot, séparé par type de cœur, avec le
  modèle ajusté ; (b) dispersion entre répétitions et entre processus.
- [`figures/campaign-repair.pdf`](figures/campaign-repair.pdf) : (a) contrôle
  A/A et (b) contrôle positif pour les trois protocoles ; (c) contrôle
  d'amorçage ; (d) contrôle d'affinité. Un point par processus, coloré selon le
  type de cœur majoritaire de ses échantillons ; en noir, médiane et intervalle
  bootstrap à 95 %.
- [`figures/campaign-warmup.pdf`](figures/campaign-warmup.pdf) : (a) coût
  normalisé selon le tour ; (b) part des processus dont le tour entier s'est
  exécuté hors cœur P.

Les axes des rapports sont logarithmiques : un rapport de 0,5 et un rapport de 2
sont à la même distance de 1, ce qui ne favorise aucun sens d'erreur.

## 10. Résultats observés et interprétation

Les chiffres sont ceux de `data/campaign` ; la réplication `v1` est donnée entre
parenthèses lorsqu'elle est utile. Ils décrivent **cette machine, ce binaire et
ces deux campagnes**.

### 10.1 Amortissement du chronométrage

| Ajustement de `C + H/N` | Processus | `H` (IC 95 %) | `C` (IC 95 %) |
|---|---:|---|---|
| Tous processus (analyse prévue) | 20 | 30,5 ns [29,4 ; 31,3] | 5,00 ns [4,47 ; 5,39] |
| Échantillons pris sur cœur P (exploratoire) | 12 | 29,7 ns [29,4 ; 30,5] | 4,40 ns [4,40 ; 4,43] |
| Échantillons pris sur cœur E (exploratoire) | 13 | 29,5 ns [29,4 ; 30,1] | 5,39 ns [5,39 ; 5,66] |

Réplication `v1` : `H` = 29,5 ns et `C` = 5,19 ns pour l'analyse prévue.

- Avec une seule opération, le coût apparent médian est de 41 ns : **7,6 à 9,3
  fois le coût réel** d'une opération selon le type de cœur. Dès 256 opérations, il est à moins de 2 % du
  plateau sur cœur P (4,59 ns contre 4,51 ns à 32 768).
- `H` ≈ 30 ns est du même ordre que les 28 ns mesurés en A1 pour deux lectures
  consécutives de l'horloge : le coût fixe est essentiellement celui du
  chronomètre. Le modèle sous-estime toutefois les très petits lots (35 ns prévus
  contre 41 ns observés pour N = 1) : un coût fixe unique ne décrit pas tout.
- `H` ne dépend presque pas du type de cœur, `C` si : 4,40 ns sur P, 5,39 ns
  sur E. Le `C` ajusté sur P reste sous le plateau observé (4,51 ns à 32 768
  opérations) : mal ajusté aux petits lots, le modèle tire `C` vers le bas. Le
  plateau est l'estimation directe du coût par opération.
- Au-delà de 64 opérations, l'écart interquartile relatif **entre processus**
  vaut 17 à 22 %, contre moins de 3 % entre processus du même type de
  cœur. Cette dispersion n'est donc pas un bruit de mesure : elle vient
  principalement du type de cœur sur lequel chaque processus a tourné (11
  processus sur 20 majoritairement sur cœur P, 10 dans `v1`).

Prédiction 1 confirmée (plateau, `H` et `C` dans les intervalles annoncés).
Prédiction 7 confirmée pour la cause invoquée, les cœurs.

### 10.2 Échelle de réparation : contrôles A/A et positif

| Protocole | `A_bis/A` médian (IC 95 %) | Processus hors ±5 % | `B/A` médian (IC 95 %) | Étendue de `B/A` |
|---|---|---:|---|---|
| Naïf, 1 opération | 0,208 [0,201 ; 0,218] | 100 % | 0,401 [0,393 ; 0,427] | 0,32 à 0,54 |
| Lot unique de 20 000 | 0,9990 [0,9988 ; 0,9991] | 20 % | 1,998 [1,998 ; 1,998] | 1,76 à 2,13 |
| Lots entrelacés | 1,0000 [1,0000 ; 1,0000] | 0 % | 2,000 [2,000 ; 2,000] | 1,93 à 2,04 |

(`v1` : 0,230 ; 0,9989 ; 1,0000 pour `A_bis/A` et 0,458 ; 1,998 ; 2,000 pour `B/A`.)

- **Conclusion trompeuse du protocole naïf.** Dans 30 processus sur 30, il
  conclurait que `A` est environ **5 fois plus lent que lui-même**, et que `B`,
  qui fait deux fois plus de travail, est **2,5 fois plus rapide** que `A`. Ce
  n'est pas du bruit : l'intervalle est étroit et le résultat se reproduit dans
  `v1`. C'est un biais systématique lié à la position du premier échantillon.
- **Lot unique.** Il corrige le biais en médiane, mais un processus sur cinq
  donnerait encore une conclusion A/A fausse de plus de 5 % (de 0,88 à 1,55) :
  une seule mesure par variante ne protège pas contre un événement ponctuel.
- **Lots entrelacés.** Aucun processus ne dépasse 5 % d'erreur A/A (0,976 à
  1,015), et `B/A` vaut 2,000 : le protocole détecte la vraie différence et
  n'en invente pas.
- Aucun effet de la position dans le tour n'est détectable dans ce protocole
  (coût normalisé médian 1,0000 aux positions 1, 2 et 3).
- Les intervalles de largeur nulle ne signifient pas une précision infinie : les
  durées sont des nombres entiers de ns, et de nombreux processus ont exactement
  la même médiane. Il faut lire l'étendue entre processus, pas seulement
  l'intervalle de la médiane.

Prédiction 2 **réfutée pour `B/A`** : nous attendions 1,05 à 1,4, soit une
sous-estimation de l'écart, et nous obtenons 0,40, un écart de sens inverse. Le
modèle « `H` constant » ignorait le coût du premier passage. Prédiction 2
confirmée pour `A_bis/A` < 1. Prédiction 3 partiellement confirmée (biais
faible en médiane, mais 20 % de conclusions fausses par processus). Prédiction 4
confirmée.

### 10.3 Contrôle exploratoire : le premier passage à froid

Protocole naïf, 30 processus par condition, médianes par processus (IC 95 %) :

| Amorçage non chronométré | A (ns) | A_bis (ns) | B (ns) | `A_bis/A` | `B/A` | Défauts de page pendant la mesure (max.) |
|---|---|---|---|---|---|---:|
| Aucun | 181 [170 ; 188] | 36 [35 ; 39] | 70,5 [69 ; 77,5] | 0,21 | 0,40 | 2 |
| Lecture d'horloge | 98,5 [96 ; 107] | 38,5 [36 ; 41,5] | 74 [70 ; 76,5] | 0,38 | 0,73 | 0 |
| Appel des fonctions | 152,5 [144,5 ; 168,5] | 36 [35 ; 37] | 57 [55,5 ; 61] | 0,23 | 0,38 | 2 |
| Mesure complète jetée | 43 [42 ; 44] | 36 [35,5 ; 37] | 47 [46 ; 47] | 0,85 | 1,10 | 0 |

- La première lecture d'horloge du processus explique environ 80 ns du surcoût de
  `A`. Lire l'horloge une fois avant fait aussi disparaître les deux défauts de
  page mineurs de la fenêtre de mesure. C'est **compatible** avec le premier
  accès aux pages du vDSO, mais ces données ne suffisent pas à l'établir.
- Le premier appel des fonctions compte aussi : environ 30 ns pour `A` et 14 ns
  pour `B`. Un appel direct ne réchauffe pas l'appel indirect de `measure`, ce qui
  peut expliquer que l'amorçage « fonctions » soit incomplet.
- Jeter une mesure complète supprime l'essentiel du biais : `B/A` = 1,10, dans
  l'intervalle prédit par `(H + 2C) / (H + C)`. Il reste 7 ns d'écart entre `A`
  et `A_bis`, que nous n'expliquons pas. Même réparé ainsi, le protocole à une
  opération reste dominé par le chronomètre.
- Aucun changement de contexte involontaire n'a eu lieu dans ces processus
  naïfs : le surcoût n'est pas une préemption.

L'hypothèse H1 est **soutenue** : c'est la première exécution des chemins de
code (horloge, puis fonctions) qui produit le biais d'ordre, pas l'ordre en
lui-même.

### 10.4 « Échauffement » et placement par l'ordonnanceur

- 26 processus sur 30 sans affinité ont pris leur premier échantillon hors cœur
  P. Tous ont ensuite été déplacés vers un cœur P, après **10,0 ms** médianes de
  travail chronométré (maximum 35,4 ms ; `v1` : 7,3 ms et 35,0 ms).
- Le coût normalisé médian vaut 1,222 pendant les premiers tours, exactement le
  rapport des coûts E et P (5,514 / 4,511 ns). Il redescend vers 1 au
  tour 23 environ : ce « ralentissement initial » est un changement de cœur, pas
  une montée progressive.
- Au tour 10, fin de l'échauffement déclaré, 57 % des processus n'étaient pas
  encore sur un cœur P. Les estimations restent correctes parce que les
  médianes portent sur 90 tours, majoritairement sur cœur P, mais un protocole
  plus court aurait mesuré un mélange de cœurs.
- Les protocoles naïf et lot unique durent moins d'une milliseconde : 26 à 28
  de leurs 30 processus n'ont jamais quitté les cœurs E.

Prédiction 5 **réfutée** : 10 tours ne suffisaient pas, et le mécanisme observé
n'est pas celui que nous avions imaginé. L'hypothèse H2 est soutenue par les
CPU enregistrés.

### 10.5 Contrôle d'affinité

| Affinité (lots entrelacés) | Processus | Coût de A, médiane (IC 95 %) | `B/A` médian |
|---|---:|---|---:|
| Sans affinité | 30 | 4,511 ns [4,511 ; 4,511] | 2,000 |
| Épinglé CPU 11 (P) | 15 | 4,511 ns [4,511 ; 4,511] | 2,000 |
| Épinglé CPU 19 (E) | 15 | 5,514 ns [5,514 ; 5,514] | 2,000 |
| Épinglé CPU 21 (LP-E) | 15 | 9,88 ns [9,19 ; 10,03] | 2,000 |

- Rapports observés : `E/P` = 1,22 et `LP-E/P` = 2,19. La prédiction 6 est
  confirmée pour l'ordre. Les fréquences maximales annoncées des CPU épinglés
  (4,7 ; 3,8 ; 2,5 GHz) donneraient 1,24 et 1,88 : proche pour E, pas pour LP-E.
  La fréquence ne suffit donc pas à expliquer les écarts, et les
  microarchitectures diffèrent.
- Le coût absolu d'une même fonction varie d'un facteur 2,2 selon le cœur, mais
  le rapport `B/A` reste 2,000 partout : **une comparaison relative entrelacée
  est bien plus robuste qu'un temps absolu**.
- Sur cœur P, deux niveaux discrets apparaissent dans les deux campagnes :
  4,511 ns et 3,607 ns par opération. 3 processus épinglés sur 15 et 1 processus
  libre sur 30 ont une médiane inférieure à 4,2 ns, avec des échantillons
  regroupés sur 3,607 ns. Le rapport des deux niveaux vaut 1,25. Deux
  états de fréquence différents sont une hypothèse plausible ; sans accès aux
  compteurs de cycles, nous ne pouvons pas la vérifier.

### 10.6 Ce que A2 permet et ne permet pas de conclure

Permet de conclure, sur cette machine :

- mesurer une opération isolée de quelques ns donne une conclusion fausse, dans
  le sens et dans l'amplitude, et ce de façon reproductible ;
- le premier échantillon d'un processus paie le premier passage dans l'horloge et
  dans le code ;
- la variabilité entre processus est dominée par le type de cœur, et un nouveau
  processus peut passer plusieurs millisecondes sur un cœur E ;
- lots, entrelacement aléatoire, contrôles A/A et positif et processus
  indépendants donnent ici, pour chaque processus, un rapport A/A juste à 2,5 %
  près et un rapport `B/A` juste à 3,5 % près.

Ne permet pas de conclure :

- le coût de `tiny_work` sur une autre machine, un autre compilateur ou une
  autre préférence énergétique ;
- la cause matérielle précise des surcoûts (vDSO, prédicteurs, TLB, fréquence) :
  aucun compteur matériel n'était accessible ;
- que 13 ms d'une requête localhost s'expliquent par ces effets. Ils font
  néanmoins entrer deux hypothèses à tester dans l'enquête : **un processus client
  neuf paie des premiers passages à froid** et **peut commencer sur un cœur E**.

## 11. Limites et expériences suivantes

- Une seule machine, deux campagnes le même jour, charge de fond non contrôlée
  (charge moyenne sur une minute entre 0,57 et 1,03 au début des campagnes).
- Le contrôle d'amorçage et la séparation par type de cœur ont été décidés
  **après** avoir vu les données : ce sont des résultats exploratoires, à
  confirmer par une campagne dont ils seraient l'objet déclaré.
- Le type de cœur « LP-E » est déduit de l'absence de cache L3 ; cette
  correspondance est une interprétation.
- La résolution entière en ns rend les médianes identiques d'un processus à
  l'autre : les intervalles de largeur nulle doivent être lus avec l'étendue.
- Explications alternatives non exclues : état de fréquence par cœur, activité du
  cœur frère en hyperthreading, décisions de l'ordonnanceur liées à la
  préférence énergétique `power`.

Expériences suivantes :

1. Relever `scaling_cur_freq` du CPU épinglé avant et après chaque processus pour
   tester l'hypothèse des deux états de fréquence sur cœur P.
2. Répéter l'échelle de réparation avec la préférence énergétique
   `performance`, **seulement avec votre accord**, car c'est un réglage global.
3. Passer à B1 avec le protocole retenu ici : processus indépendants, lots
   entrelacés dans un ordre aléatoire, mesure jetée, type de cœur enregistré ou
   épinglage explicite, contrôles A/A et positif.
4. Dans l'enquête J, séparer premier appel et appels suivants d'un client neuf,
   et relever son type de cœur.

## 12. Compréhension et prolongement

Questions :

1. Pourquoi le protocole naïf a-t-il pu conclure que `B` est plus rapide que `A`,
   alors que le modèle `H + N × C` prévoyait seulement un écart écrasé ?
2. Pourquoi la médiane `A_bis/A` du lot unique est-elle correcte alors qu'un
   processus sur cinq donne une conclusion fausse ? Quelle conclusion un
   doctorant qui n'aurait lancé qu'**un** processus aurait-il pu défendre ?
3. Qu'est-ce qui distingue ici un échauffement d'un changement de cœur, et
   quelle donnée brute a permis de trancher ?
4. Le coût absolu varie d'un facteur 2,2 entre cœurs, mais pas le rapport `B/A`.
   Qu'en déduire pour présenter une comparaison de performance ?
5. Pourquoi les intervalles bootstrap de largeur nulle ne sont-ils pas une
   preuve de précision parfaite ?

Prolongement : écrire une variante `C` qui calcule le même résultat que `A` par
un chemin de code distinct (par exemple la fonction de référence intégrée), puis
utiliser le protocole entrelacé pour estimer `C/A` avec son intervalle. Avant de
mesurer, écrire la prédiction et le critère qui la réfuterait.
