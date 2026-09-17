# B1 - Calcul et compilation : optimisation, travail éliminé, assembleur

## 1. Question et prérequis

**Question :** quand on chronomètre une boucle de calcul écrite en C, mesure-t-on
le calcul écrit dans le source ? Comment le compilateur et son niveau
d'optimisation changent-ils le travail réellement exécuté, et comment vérifier
qu'il existe encore avant d'interpréter une durée ?

Prérequis : [A2](../02-microbenchmark/README.md), dont ce projet reprend le
protocole (processus indépendants, lots, ordre aléatoire, mesure jetée, contrôles
A/A et positif, épinglage sur un cœur P). Aucune connaissance préalable de
l'assembleur n'est supposée.

## 2. Notions nécessaires

- **Niveau d'optimisation** (*optimization level*) : `-O0` traduit presque ligne
  à ligne et garde chaque variable en mémoire ; `-O1`, `-O2` et `-O3` autorisent
  des transformations de plus en plus nombreuses. Intuitivement, le compilateur
  n'est pas un traducteur mot à mot mais un rédacteur qui peut réécrire le texte
  tant que le sens observable reste le même.
- **Comportement observable** (*observable behavior*) : ce que la norme C oblige
  à préserver (résultats renvoyés, écritures, appels externes). Le temps pris
  **n'en fait pas partie** : un calcul dont rien ne dépend peut disparaître.
- **Élimination du code mort** (*dead code elimination*) : suppression d'un
  calcul dont le résultat n'est jamais utilisé.
- **Formule fermée** (*closed form*, *final value replacement*) : remplacement
  d'une boucle par une expression qui donne directement sa valeur finale, par
  exemple `0 + 1 + ... + (n - 1) = n (n - 1) / 2`.
- **Vectorisation** (*vectorization*, *SIMD*) : traitement de plusieurs éléments
  par instruction avec des registres larges (`xmm` : 128 bits). Étudiée en B2 ;
  ici, seulement repérée dans l'assembleur.
- **Assembleur** (*assembly*) : forme lisible des instructions machine.
  `objdump -d -M intel` l'affiche en syntaxe Intel, où la destination est à
  gauche : `add rax, QWORD PTR [rdi]` ajoute à `rax` le mot de 64 bits lu à
  l'adresse `rdi`.
- **Boucle en assembleur** : un saut conditionnel (`jne`, `jb`...) vers une
  adresse **antérieure** de la même fonction.
- **Unité de traduction** (*translation unit*) : fichier C compilé séparément.
  Sans optimisation à l'édition de liens (*LTO*), le compilateur ne voit pas le
  code d'une autre unité et ne peut pas l'intégrer à l'appelant.
- **Coût par élément et débit** (*cost per element*, *throughput*) : durée
  divisée par le nombre d'éléments traités, et son inverse.

Ce qui est **garanti** : le résultat renvoyé est le même à tous les niveaux pour
un programme sans comportement indéfini (vérifié ici). Ce qui **dépend du
compilateur** : quelles transformations sont appliquées, et à quel niveau. Ce qui
**dépend de la machine** : le coût des instructions restantes.

## 3. Montage expérimental

Quatre noyaux dans [`src/kernels.c`](src/kernels.c), compilés par **GCC 15.2** et
**Clang 21.1** à `-O0`, `-O1`, `-O2` et `-O3` (8 binaires). Le harnais
[`src/harness.c`](src/harness.c) est compilé une seule fois par GCC à `-O2` : seul
le code des noyaux change d'un binaire à l'autre.

| Mesure | Noyau appelé | Rôle |
|---|---|---|
| `sum_array` | somme des éléments, résultat renvoyé | cas étudié |
| `sum_array_bis` | la même fonction | contrôle A/A |
| `sum_array_twice` | deux parcours complets | contrôle positif (rapport attendu 2) |
| `sum_discarded` | somme calculée puis ignorée | piège : travail sans effet observable |
| `sum_indices` | `0 + 1 + ... + (n - 1)`, résultat renvoyé | piège : formule fermée possible |

Tailles : `n = 64, 256, ..., 4 194 304` (puissances de 4, soit jusqu'à 32 Mio de
données). Chaque échantillon appelle le noyau `max(1, 2^22 / n)` fois : environ
4 millions d'éléments par échantillon, pour que le chronomètre (environ 30 ns
selon A2) reste négligeable, **sauf si le travail a disparu**.

## 4. Analyse statique et prédictions, écrites avant toute mesure

### 4.1 Ce que montre l'assembleur

[`disasm.py`](disasm.py) extrait chaque noyau de chaque binaire
([`reports/assembly.csv`](reports/assembly.csv), extraits dans
[`reports/asm/`](reports/asm/)). Nous l'avons lu **avant** de mesurer ; c'est la
méthode visée : lire le code exécuté, prédire la forme de la courbe, puis mesurer.

| Noyau | GCC -O0 | GCC -O1 | GCC -O2 | GCC -O3 | Clang -O0 | Clang -O1 | Clang -O2 | Clang -O3 |
|---|---|---|---|---|---|---|---|---|
| `sum_array` | boucle, pile | boucle | boucle | boucle SSE2, 2 voies | boucle, pile | boucle | boucle SSE2, 4 voies | idem -O2 |
| `sum_array_twice` | 2 boucles | 2 boucles | 2 boucles | 2 boucles SSE2 | 2 boucles | 2 boucles | 2 boucles SSE2 | idem -O2 |
| `sum_discarded` | boucle, pile | **boucle vide** | **`xor eax,eax ; ret`** | **idem** | boucle, pile | **`xor eax,eax ; ret`** | **idem** | **idem** |
| `sum_indices` | boucle, pile | boucle | boucle par pas de 2 | idem -O2 | boucle, pile | **formule, sans boucle** | **idem** | **idem** |

Exemples, GCC 15.2 :

```asm
; sum_array, -O2 : une lecture mémoire et une addition par élément
add    rax, QWORD PTR [rdi]
add    rdi, 0x8
cmp    rdi, rdx
jne    <sum_array+0x10>

; sum_discarded, -O2 : la boucle a disparu, la fonction renvoie 0
xor    eax, eax
ret

; sum_discarded, -O1 : les lectures ont disparu, mais un compteur vide subsiste
add    rax, 0x1
cmp    rsi, rax
jne    <sum_discarded+0xf>
```

Clang 21.1 à -O1, `sum_indices` : aucun saut arrière, une multiplication
(`mul rcx`) ; la boucle est remplacée par la formule.

### 4.2 Prédictions

Hypothèse de travail pour les ordres de grandeur : environ 4 GHz effectifs sur le
CPU 11, donc environ 0,25 ns par cycle, sans supposer qu'une instruction coûte un
cycle.

1. **Travail proportionnel ou constant.** Le coût par élément est à peu près
   constant avec `n` quand l'assembleur contient une boucle qui parcourt les
   éléments, et décroît comme `1/n` quand il n'en contient pas. Critère fixé à
   l'avance : pente log-log du coût par élément inférieure à -0,5 signifie
   « travail constant ». Nous prédisons l'accord entre ce critère et l'assembleur
   pour les 32 couples (binaire, noyau).
2. **`sum_discarded` :** « débit » absurde (coût par élément de l'ordre de
   10^-5 ns à `n = 2^22`) pour GCC -O2/-O3 et Clang -O1/-O2/-O3 ; coût proche de
   `sum_array` au même niveau pour les deux -O0 ; GCC -O1 garde un coût
   proportionnel à `n` sans lire le tableau.
3. **`sum_indices` :** proportionnel à `n` pour les 4 niveaux GCC, constant pour
   Clang -O1 à -O3.
4. **`sum_array`, taille 65 536 (512 Kio, dans le cache L2 du cœur) :**
   0,2 à 0,4 ns par élément pour les boucles scalaires optimisées (environ un
   cycle par élément) ; rapport `-O0 / -O2` entre 3 et 8, car -O0 relit et réécrit
   la somme et l'indice en mémoire à chaque itération ; GCC -O3 plus rapide que
   GCC -O2 d'un facteur 1,2 à 2 ; Clang -O2 plus rapide que GCC -O2 d'un facteur
   1,5 à 4.
5. **Grandes tailles (4 Mio à 32 Mio) :** hausse possible du coût par élément,
   surtout pour les versions vectorisées, et resserrement des écarts entre
   binaires. Nous ne prétendrons pas identifier un niveau de cache sur la seule
   forme de la courbe ; c'est l'objet de C1.
6. **Coût fixe par appel :** à `n = 64`, un surcoût `F / n` visible, avec `F` de
   quelques ns (appel indirect, entrée et sortie de boucle).
7. **Contrôles :** `sum_array_bis / sum_array` entre 0,97 et 1,03 par processus ;
   `sum_array_twice / sum_array` entre 1,8 et 2,1 pour tous les binaires, puisque
   les deux boucles ne sont fusionnées nulle part.
8. **Suite de A2 :** si deux niveaux de coût réapparaissent sur le CPU 11, les
   processus du niveau rapide devraient montrer une fréquence
   `scaling_cur_freq` plus élevée. Test faible : la fréquence n'est relevée
   qu'avant et après la phase de mesure.

## 5. Code et commandes

- [`src/kernels.c`](src/kernels.c) : les quatre noyaux, seul fichier dont la
  compilation varie.
- [`src/harness.c`](src/harness.c) : plan des mesures construit avant la première
  mesure, appels indirects groupés, vérification de chaque résultat après la
  phase de mesure, fréquence et `getrusage` autour de la phase de mesure.
- [`disasm.py`](disasm.py) : analyse statique du code machine.
- [`prepare.py`](prepare.py), [`run.sh`](run.sh) : plan des processus dans un ordre
  aléatoire fixé, épinglage sur le CPU 11 (P, comme en A2).
- [`verify.py`](verify.py) : complétude, épinglage, exactitude des résultats et
  recalcul indépendant en Python.
- [`analyze.py`](analyze.py) : résumés et figures selon
  [`STYLE_FIGURES.md`](../../STYLE_FIGURES.md).

```sh
make check      # correction : autotests des 8 binaires, rejeu Python
make assembly   # analyse statique seule
make quick      # validation de la chaîne
make campaign   # campagne documentée ; refuse d'écraser data/campaign
make analyze    # résumés et figures depuis data/campaign
```

Compilation exacte d'un binaire, par exemple Clang -O2 :

```sh
gcc -O2 -std=c17 -Wall -Wextra -Wpedantic -c src/harness.c -o build/harness.o
clang -O2 -std=c17 -Wall -Wextra -Wpedantic -DKERNEL_OPT='"clang-O2"' -c src/kernels.c -o build/kernels-clang-O2.o
gcc build/harness.o build/kernels-clang-O2.o -o build/bench-clang-O2
```

## 6. Vérification de correction, indépendante de la mesure

- `--self-test` de chaque binaire : les quatre noyaux comparés à une somme de
  référence écrite dans le harnais, pour 7 tailles dont 0, 1 et une taille
  impaire.
- Après la phase de mesure, le harnais compare **chaque** résultat accumulé à sa
  valeur attendue et refuse de terminer normalement en cas d'écart.
- `verify.py` : tous les binaires donnent le même résultat pour un même noyau et
  une même taille ; avec `--replay`, les valeurs attendues sont recalculées en
  Python (SplitMix64 réimplémenté).
- `sum_discarded` renvoie 0 par construction : **aucune vérification de résultat
  ne peut prouver que sa boucle a tourné**. Seuls l'assembleur et la mesure le
  peuvent ; c'est précisément le piège étudié.

## 7. Protocole de la campagne

- 8 binaires × 15 processus indépendants = 120 processus, dans un ordre aléatoire
  fixé (graine `20260916`), tous épinglés sur le CPU 11.
- Dans chaque processus : 16 tours ; dans chaque tour, les 45 couples (mesure,
  taille) dans un ordre tiré au hasard. Le premier tour est déclaré échauffement
  et exclu des estimations, mais conservé.
- Unité statistique : le processus. Pour chaque processus, mesure et taille : coût
  par élément médian sur les 15 tours retenus.
- Entre processus : médiane, écart interquartile et intervalle bootstrap
  percentile à 95 % (10 000 rééchantillonnages).
- Pente : moindres carrés de `log2(coût par élément)` en fonction de `log2(n)`,
  sur les médianes entre processus des 9 tailles. Critère : pente < -0,5.
- Coût fixe par appel : ajustement de `c + F / n` pour `sum_array`, sur les tailles
  64 à 65 536.
- Contrôles par processus : médiane sur les 9 tailles des rapports
  `sum_array_bis / sum_array` et `sum_array_twice / sum_array`.
- Fréquence : corrélation de rang (Spearman) entre le coût normalisé de
  `sum_array` à `n = 65 536` et `scaling_cur_freq` relevée après la mesure.
- Même tableau (graine fixe), aligné sur une page, initialisé avant la mesure.
  Aucun réglage global de la machine.

## 8. Données brutes

- [`data/campaign/`](data/campaign/) : `plan.csv` (écrit avant la mesure),
  `topology.csv`, un fichier `run-NNN.csv` par processus (une ligne par
  échantillon : binaire, tour, position, mesure, taille, nombre d'appels, durée,
  CPU avant et après, résultat et valeur attendue) et `run-NNN-meta.csv`
  (compilateur, fréquence relevée avant et après, `getrusage`).
- [`data/environment-campaign.txt`](data/environment-campaign.txt) : machine,
  versions, commandes de compilation, empreintes SHA-256 des sources et des
  8 binaires.
- [`reports/assembly.csv`](reports/assembly.csv) et [`reports/asm/`](reports/asm/) :
  analyse statique.
- Résumés : `reports/campaign-costs.csv` (coût par élément, débit, par binaire,
  mesure et taille), `-slopes.csv`, `-model.csv`, `-controls.csv`,
  `-speedup.csv`, `-frequency.csv`, `-frequency-summary.csv`.

Les 86 400 échantillons (81 000 hors tour d'échauffement) ont tous un résultat exact. Aucune observation n'a été
retirée.

## 9. Figures

- [`figures/campaign-scaling.pdf`](figures/campaign-scaling.pdf) : `sum_array`
  pour GCC (a à c) et Clang (d à f) ; durée d'un appel, coût par élément avec
  écart interquartile entre processus, débit.
- [`figures/campaign-eliminated.pdf`](figures/campaign-eliminated.pdf) :
  coût apparent par élément de `sum_discarded` et `sum_indices`. Chaque libellé
  donne la pente mesurée et la présence d'une boucle dans l'assembleur : deux
  preuves indépendantes, côte à côte.
- [`figures/campaign-controls.pdf`](figures/campaign-controls.pdf) : (a) contrôle
  A/A et (b) contrôle positif, un point par processus ; (c) accélération par
  rapport à -O0 du même compilateur, à 512 Kio et 32 Mio ; (d) fréquence relevée
  et coût normalisé.

Lire le débit en même temps que le coût par élément : ce sont deux vues de la même
mesure. Le coût par élément rend les petites différences lisibles ; le débit dit
combien de travail est fait par seconde. Une durée d'appel qui croît
proportionnellement à `n` apparaît comme une droite de pente 1 en log-log (a, d).

## 10. Résultats observés et interprétation

Chiffres de la campagne, **sur cette machine, pour ces binaires et le CPU 11**.

### 10.1 Le travail éliminé se voit dans la pente

| Mesure | Travail constant selon la pente (< -0,5) | Sans boucle dans l'assembleur |
|---|---|---|
| `sum_discarded` | GCC -O2, -O3 ; Clang -O1, -O2, -O3 | les mêmes |
| `sum_indices` | Clang -O1, -O2, -O3 | les mêmes |
| `sum_array`, `_bis`, `_twice` | aucun | aucun |

Accord entre la pente et l'assembleur : **40 mesures sur 40** (32 couples
binaire-noyau distincts). Prédiction 1 confirmée.

- Pour une fonction éliminée, un appel coûte environ 1,6 ns (appel indirect,
  `xor eax,eax`, `ret`, addition de l'accumulateur). À `n = 4 194 304`, un seul
  appel par échantillon : la durée mesurée, 41 à 49 ns, est alors **celle du
  chronomètre** (A2 : `H` ≈ 30 ns). Le « coût par élément » vaut 1,1 × 10⁻⁵ ns,
  soit un débit apparent d'environ 90 000 milliards d'éléments par seconde.
- La pente mesurée vaut -0,74 et non -1. Le modèle
  `coût par élément = 1,6 / n + H / 2^22` l'explique : aux petites tailles, le
  coût d'appel domine (pente -1) ; aux grandes, le chronomètre domine (pente 0).
  Il reproduit les deux extrémités (0,025 ns à `n = 64`, 1,1 × 10⁻⁵ ns à
  `n = 2^22`).
- `sum_discarded` à -O0 coûte autant que `sum_array` au même niveau (GCC :
  3,06 contre 3,06 ns ; Clang : 1,02 contre 1,02 ns). Prédiction 2 confirmée.
- GCC -O1 est un cas intermédiaire : pente -0,07, boucle présente, mais coût de
  0,203 ns par élément, **la moitié** de `sum_array` au même niveau. Les lectures
  mémoire ont disparu, pas la boucle. Un benchmark qui mesurerait ce binaire
  conclurait à une somme deux fois plus rapide qu'elle ne l'est.
- `sum_indices` : les quatre niveaux GCC restent proportionnels à `n`
  (0,41 ns par élément à -O1, -O2 et -O3) ; Clang -O1 à -O3 calcule la formule en
  environ 1,6 ns quel que soit `n`. Prédiction 3 confirmée.

**Leçon :** un résultat correct ne prouve pas que la boucle a tourné
(`sum_indices` chez Clang), et une boucle absente ne produit aucune erreur
(`sum_discarded`). Seuls l'assembleur et la forme de la courbe selon `n` le
révèlent.

### 10.2 Coût de `sum_array` selon le compilateur et le niveau

À `n = 65 536` (512 Kio), médiane entre 15 processus :

| Binaire | ns par élément (IC 95 %) | Débit (10⁹ éléments/s) | Accélération / -O0 | Assembleur |
|---|---|---:|---:|---|
| GCC -O0 | 3,055 [3,043 ; 3,066] | 0,33 | 1 | pile |
| GCC -O1 | 0,417 [0,415 ; 0,419] | 2,40 | 7,3 | scalaire |
| GCC -O2 | 0,415 [0,414 ; 0,419] | 2,41 | 7,4 | scalaire |
| GCC -O3 | 0,204 [0,203 ; 0,207] | 4,90 | 15,0 | SSE2, 2 voies |
| Clang -O0 | 1,021 [1,013 ; 1,029] | 0,98 | 1 | pile |
| Clang -O1 | 0,416 [0,415 ; 0,416] | 2,40 | 2,5 | scalaire |
| Clang -O2 | 0,140 [0,139 ; 0,140] | 7,16 | 7,3 | SSE2, 4 voies |
| Clang -O3 | 0,140 [0,140 ; 0,141] | 7,13 | 7,3 | SSE2, 4 voies |

- Les boucles scalaires optimisées des deux compilateurs coûtent la même chose
  (0,415 à 0,417 ns) : même code machine, même coût.
- **« -O0 » ne désigne pas un programme de référence** : GCC -O0 est 3,0 fois plus
  lent que Clang -O0. Une accélération « par rapport à -O0 » dépend donc du
  compilateur (7,4 contre 2,5 à -O1).
- À -O2, Clang est 2,97 fois plus rapide que GCC [2,95 ; 3,01] ; à -O3, 1,46 fois.
  L'écart vient du code produit, pas du langage.
- Vectoriser en 2 voies divise le coût par 2,03 ; en 4 voies, par 2,97 seulement.

Prédiction 4 : rapport -O0 / -O2 de 7,4 (GCC) et 7,3 (Clang), dans l'intervalle
annoncé ; Clang -O2 / GCC -O2 = 2,97, dans l'intervalle. Deux écarts de peu : le
coût scalaire (0,41 ns) dépasse la borne haute annoncée (0,4 ns), et le gain de
GCC -O3 (2,03) la borne haute de 2.

### 10.3 Grandes tailles : les écarts se referment

- À `n = 4 194 304` (32 Mio), tous les binaires optimisés convergent vers
  0,71 à 0,77 ns par élément, soit 1,3 à 1,4 × 10⁹ éléments par seconde, environ
  10 à 11 Go de données lues par seconde.
- L'accélération de GCC -O3 par rapport à GCC -O0 tombe de 15,0 à 4,5 ; celle de
  Clang -O2 de 7,3 à 1,6. La hausse commence vers 262 144 éléments (2 Mio).
- Hypothèse : au-delà de ce que les caches contiennent, le débit est limité par
  l'accès à la mémoire plutôt que par les instructions de la boucle. La forme de la
  courbe ne suffit pas à identifier un niveau de cache ; C1 le testera.

Prédiction 5 confirmée.

### 10.4 Coût fixe par appel

Ajustement `c + F / n` sur `n` = 64 à 65 536 :

| Binaire | `F` (ns par appel) |
|---|---:|
| GCC -O1, -O2 ; Clang -O1 (scalaires) | 11,5 à 12,3 |
| GCC -O3 (2 voies) | 3,7 |
| Clang -O2, -O3 (4 voies) | 1,6 |
| Clang -O0 | 26 |
| GCC -O0 | modèle inadapté (le coût croît de 1,98 à 3,05 ns avec `n`) |

Prédiction 6 partiellement confirmée. Le coût fixe des boucles scalaires, environ
12 ns, dépasse nettement celui des boucles vectorisées, pourtant plus longues à
préparer. Hypothèse pour B2 : la sortie d'une boucle de 64 itérations est mal
prédite, alors qu'une boucle de 16 itérations (4 éléments par itération) l'est
bien.

### 10.5 Contrôles

- A/A : rapports par processus de 0,989 à 1,014 ; aucun processus hors ±5 %.
- Contrôle positif : `sum_array_twice / sum_array` de 1,953 à 2,050 pour tous les
  binaires, y compris vectorisés.

Prédiction 7 confirmée : le protocole issu d'A2 mesure juste, et c'est ce qui rend
crédibles les écarts de 3 à 15 entre binaires.

### 10.6 Fréquence : test non concluant

`scaling_cur_freq` vaut presque toujours 2,4 ou 2,5 GHz, avant comme après la
mesure, et n'est pas corrélée au coût (Spearman -0,08, 120 processus). Les deux
niveaux de coût observés en A2 ne sont pas réapparus : le coût normalisé varie
de 0,979 à 1,033.

Or la boucle vide de GCC -O1 dure 0,203 ns par itération : moins d'un demi-cycle à
2,45 GHz, et même moins d'un cycle à la fréquence maximale annoncée de 4,7 GHz
(0,213 ns). Donc au moins une hypothèse est fausse : soit la valeur relevée ne
décrit pas la fréquence pendant la mesure, soit une itération peut coûter moins
d'un cycle sur ce processeur, soit la fréquence maximale annoncée est inexacte.
Sans compteur de cycles, **nous ne pouvons pas trancher**. La prédiction 8 n'est
ni confirmée ni réfutée, et `scaling_cur_freq` ne doit pas servir d'observable.

### 10.7 Ce que B1 permet et ne permet pas de conclure

Permet de conclure, sur cette machine :

- le code mesuré peut différer radicalement du source : boucles supprimées,
  remplacées par une formule, allégées ou vectorisées, selon le compilateur et le
  niveau ;
- la pente du coût selon `n` et l'assembleur détectent ces transformations de
  façon concordante ;
- pour la même boucle source, le coût varie d'un facteur 22 entre binaires à
  512 Kio (GCC -O0 contre Clang -O2), et ces écarts se réduisent fortement à
  32 Mio.

Ne permet pas de conclure :

- ce que coûte une instruction en cycles (aucun compteur disponible) ;
- quelle ressource limite les grandes tailles ;
- que Clang « est meilleur » en général : quatre noyaux très simples, une version
  de chaque compilateur, un processeur.

Pour l'enquête sur les 13 ms : un même programme peut être 3 à 15 fois plus lent
compilé sans optimisation. **Le mode de compilation du client et du serveur
d'origine devient une hypothèse à vérifier** avant toute mesure de réseau.

## 11. Limites et expériences suivantes

- Un seul CPU logique (11), une seule campagne ; charge moyenne sur une minute de
  0,69 au début.
- Le CPU 11 n'est pas réservé : jusqu'à 216 changements de contexte involontaires
  dans un processus GCC -O0 (une dizaine de secondes de mesure). Les médianes sur
  15 tours y résistent, mais la dispersion n'est pas celle d'une machine isolée.
- Détection des boucles par sauts arrière : heuristique (un saut arrière vers un
  `ret` serait compté), vérifiée à la main seulement sur les extraits cités en
  section 4.1.
- Les binaires ne diffèrent que par les noyaux ; un effet d'alignement du code
  entre binaires n'est pas exclu.
- Aucune option `-march` : le jeu d'instructions reste x86-64 de base (SSE2).

Expériences suivantes :

1. **B2** : dépendances entre instructions, vectorisation et prédiction de
   branchement ; tester l'hypothèse du coût fixe scalaire avec `n` = 16 à 128 et
   comparer `-march=native`.
2. **C1** : parcours mémoire, pour expliquer la convergence des débits au-delà
   de 2 Mio.
3. Demander votre accord pour abaisser `perf_event_paranoid` le temps d'une
   session : cycles et instructions par élément trancheraient la question de la
   section 10.6.

## 12. Compréhension et prolongement

Questions :

1. Pourquoi `sum_discarded` a-t-elle le droit de ne rien faire à -O2, et pourquoi
   aucun test de résultat ne peut-il le révéler ?
2. La pente mesurée d'une fonction éliminée vaut -0,74 et non -1. Que mesure-t-on
   à `n = 4 194 304`, et quelle notion d'A2 cela illustre-t-il ?
3. Pourquoi « -O2 est 7 fois plus rapide que -O0 » n'est-il pas une phrase
   défendable sans nommer le compilateur, la taille et la machine ?
4. Clang calcule `sum_indices` sans boucle mais GCC non. Qu'est-ce qui est
   garanti par le langage, et qu'est-ce qui dépend du compilateur ?
5. Pourquoi les écarts entre binaires se réduisent-ils à 32 Mio, et pourquoi la
   forme de la courbe ne suffit-elle pas à nommer la cause ?

Prolongement : écrire `sum_volatile`, qui ajoute chaque élément à une variable
`volatile`, puis prédire, avant de mesurer, la pente et le coût à -O2. Vérifier
dans l'assembleur ce que `volatile` oblige le compilateur à faire, et expliquer
pourquoi ce n'est pas une bonne façon de « protéger » un benchmark.
