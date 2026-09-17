# B2 - Dépendances et branches : parallélisme d'instructions, vectorisation, prédiction de branchement

## 1. Question et prérequis

**Question :** à nombre d'instructions égal, pourquoi une boucle peut-elle être
plusieurs fois plus lente qu'une autre ? Plus précisément, que coûtent sur cette
machine une dépendance entre itérations et un branchement imprévisible, et que
change le code produit par le compilateur (instruction conditionnelle,
vectorisation) ?

Prérequis : [B1](../03-compilation/README.md) (lire l'assembleur avant de mesurer,
protocole de mesure, 0,415 ns par élément pour une somme scalaire sur le CPU 11) et
[A2](../02-microbenchmark/README.md) (processus indépendants, contrôles A/A et
positif).

## 2. Notions nécessaires

**Intuition.** Un processeur moderne est une chaîne de montage qui avance sur
plusieurs postes à la fois et **parie** sur la suite du programme pour ne pas
attendre. Deux choses le ralentissent : une tâche qui attend le résultat de la
précédente, et un pari perdu.

- **Exécution dans le désordre** (*out-of-order execution*) : le processeur exécute
  les instructions dès que leurs entrées sont prêtes, pas forcément dans l'ordre du
  programme.
- **Parallélisme au niveau des instructions** (*instruction-level parallelism*) :
  plusieurs instructions indépendantes avancent pendant le même cycle.
- **Chaîne de dépendance portée par la boucle** (*loop-carried dependency chain*) :
  suite d'instructions dont chacune attend le résultat de l'itération précédente.
  Sa **latence** (*latency*), en cycles, borne la vitesse de la boucle quel que soit
  le nombre d'étages disponibles.
- **Branchement conditionnel** (*conditional branch*) : saut qui dépend d'une
  donnée. **Prédiction de branchement** (*branch prediction*) : le processeur devine
  la direction et exécute la suite par anticipation (*speculative execution*).
  **Mauvaise prédiction** (*misprediction*) : le travail anticipé est jeté et
  l'exécution reprend, pour une pénalité de l'ordre de 15 à 20 cycles selon les
  descriptions publiques des microarchitectures récentes (ordre de grandeur, non
  mesuré ici).
- **Instruction conditionnelle sans branchement** (*branchless code* ; `cmov`, `sbb`,
  `setcc`) : le résultat est calculé dans tous les cas, puis choisi. Aucun pari,
  donc aucune pénalité, mais les deux chemins sont toujours payés.
- **Vectorisation** (*SIMD*) : plusieurs éléments traités par instruction ; une
  condition devient un **masque** (*mask*), un mot de bits par élément.
  `-march=x86-64-v3` autorise AVX2 : registres `ymm` de 256 bits, soit 4 entiers de
  64 bits.
- **Déroulage de boucle** (*loop unrolling*) : le compilateur écrit plusieurs
  itérations par tour de boucle ; « déroulé ×4 » signifie 4 éléments par tour.

### Notations

**Binaires.** Les noyaux de [`src/kernels.c`](src/kernels.c) sont compilés avec six
jeux d'options ; le harnais est compilé une seule fois par GCC `-O2`.

| Binaire | Options des noyaux |
|---|---|
| `gcc-scalar` | GCC 15.2 `-O2 -fno-tree-vectorize -fno-if-conversion -fno-if-conversion2` |
| `gcc-O2` | GCC `-O2` |
| `gcc-O3-v3` | GCC `-O3 -march=x86-64-v3` (AVX2) |
| `clang-scalar` | Clang 21.1 `-O2 -fno-vectorize -fno-slp-vectorize` |
| `clang-O2` | Clang `-O2` |
| `clang-O3-v3` | Clang `-O3 -march=x86-64-v3` |

Clang n'offre pas d'option documentée pour interdire les instructions
conditionnelles : `clang-scalar` n'est « scalaire » que pour la vectorisation.

**Partie 1, dépendances.** $x_i$ est le $i$-ème élément d'un tableau aléatoire,
$K$ la constante impaire `0x9e3779b97f4a7c15`, et $\oplus$ le ou exclusif (xor).

| Mesure | Calcul par élément | Chaîne portée par la boucle |
|---|---|---|
| `chain_xor_mul` | $h \leftarrow (h \oplus x_i) \times K$ | xor puis multiplication |
| `split_xor_mul` | $h \leftarrow h \oplus (x_i \times K)$ | xor seulement ; la multiplication ne dépend que de $x_i$ |
| `sum_one` | $s \leftarrow s + x_i$ | une addition |
| `sum_one_bis` | la même fonction que `sum_one` | contrôle A/A : rapport vrai 1 |
| `sum_four` | 4 accumulateurs, chacun reçoit un élément sur quatre | 4 chaînes indépendantes d'une addition |
| `sum_twice` | deux parcours complets du tableau, chacun faisant la somme | contrôle positif : rapport attendu 2 |

`chain_xor_mul` et `split_xor_mul` font exactement les mêmes opérations par élément
(une lecture, un xor, une multiplication) : seule la place de la multiplication par
rapport à la dépendance change.

**Partie 2, branchements.** Un élément est **retenu** quand $x_i \geq 2^{63}$.

| Mesure | Ce qu'elle fait |
|---|---|
| `sum_if` | somme des éléments retenus, écrite avec `if` |
| `filter_copy` | copie des éléments retenus dans un tampon, écrite avec `if` |
| `filter_copy_mask` | même filtre sans branchement : écriture systématique, avance conditionnelle du curseur |

Neuf jeux de données de 65 536 éléments, contenant chacun exactement
$\operatorname{round}(p \times 65\,536)$ éléments retenus :

| Jeu | Ordre des éléments |
|---|---|
| **mélangé**, $p$ = 0 ; 0,1 ; 0,25 ; 0,5 ; 0,75 ; 0,9 ; 1 | aléatoire, **renouvelé avant chaque échantillon** (hors chronométrage), pour que le prédicteur ne puisse pas apprendre une séquence répétée |
| **trié**, $p = 0{,}5$ | exactement les mêmes valeurs, les éléments retenus tous à la fin |
| **alterné**, $p = 0{,}5$ | un élément non retenu, un élément retenu, et ainsi de suite |

Pour un $p$ donné, le résultat ne dépend donc pas de l'ordre : seul le motif de la
condition change.

**Partie 3, petites boucles** : `sum_one` pour $n$ = 1 à 1 024 éléments (20 tailles).

**Symboles :**

| Symbole | Signification | Unité |
|---|---|---|
| $n$ | nombre d'éléments traités par un appel | |
| $p$ | probabilité de prise : part des éléments retenus | |
| $c$ | coût par élément : durée d'un échantillon divisée par le nombre d'éléments traités ; médiane des tours mesurés dans un processus | ns |
| $c_{\text{chain}}/c_{\text{split}}$ | rapport de `chain_xor_mul` à `split_xor_mul`, par processus | |
| $c_{\text{one}}/c_{\text{four}}$ | rapport de `sum_one` à `sum_four`, par processus | |
| $c_{\text{bis}}/c_{\text{one}}$, $c_{\text{twice}}/c_{\text{one}}$ | contrôles A/A et positif | |
| $c_{\text{mél}}/c_{\text{trié}}$, $c_{\text{alt}}/c_{\text{trié}}$ | à $p = 0{,}5$, rapport du jeu mélangé ou alterné au jeu trié | |
| $m(p)$ | taux de mauvaises prédictions par élément | |
| $c_0$ | coût par élément quand la condition est toujours prévisible | ns |
| $P$ | pénalité d'une mauvaise prédiction | ns |
| $R^2$ | coefficient de détermination d'un ajustement (1 : ajustement parfait) | |
| $T(n)$ | durée d'un appel de `sum_one` sur $n$ éléments | ns |
| $a$, $b$ | ordonnée à l'origine et pente de la droite $T(n) = a + b\,n$ | ns, ns par élément |
| $e(n)$ | écart à la droite, $e(n) = T(n) - (a + b\,n)$ | ns |

Ce qui est **garanti** : les résultats, identiques pour tous les binaires (vérifié).
Ce qui **dépend du compilateur** : la forme donnée à une condition et la
vectorisation. Ce qui **dépend de la machine** : latences, pénalité de mauvaise
prédiction, qualité du prédicteur. Aucun compteur matériel n'est accessible
(`perf_event_paranoid=4`) : les mauvaises prédictions ne sont **pas comptées**,
seulement déduites de durées sous des hypothèses explicites.

## 3. Analyse statique et prédictions, écrites avant la campagne

### 3.1 Ce que montre l'assembleur

[`disasm.py`](disasm.py) produit [`reports/assembly.csv`](reports/assembly.csv) et les
extraits de [`reports/asm/`](reports/asm/). Son repérage des branchements dans une
boucle compte aussi les sauts de gestion des queues de boucle ; la classification
des noyaux conditionnels ci-dessous a donc été vérifiée à la main.

| Noyau | gcc-scalar | gcc-O2 | gcc-O3-v3 | clang-scalar | clang-O2 | clang-O3-v3 |
|---|---|---|---|---|---|---|
| `sum_if` | **branchement** | `cmov` | masque AVX2 | `cmov` | `cmov` | masque AVX2 |
| `filter_copy` | **branchement** | **branchement** | **branchement** | **branchement** | **branchement** | **branchement** |
| `filter_copy_mask` | `sbb` | `sbb` | `sbb` | `sbb` | `sbb` | `sbb` |
| `chain_xor_mul` | scalaire | scalaire | scalaire | scalaire, déroulé ×4 | scalaire, déroulé ×4 | scalaire, déroulé ×8 |
| `split_xor_mul` | scalaire | scalaire | AVX2 | scalaire | SSE2 | AVX2 |
| `sum_one` | scalaire | scalaire | AVX2 | scalaire | SSE2 | AVX2 |
| `sum_four` | 4 accumulateurs | SSE2 | AVX2 | 4 accumulateurs | 4 accumulateurs | AVX2 |

Trois observations structurent les prédictions :

- **`chain_xor_mul` n'est vectorisée par aucun compilateur**, alors que
  `split_xor_mul`, aux opérations identiques, l'est trois fois : la dépendance entre
  itérations interdit de traiter plusieurs éléments en même temps. La multiplication
  vectorielle de 64 bits est émulée (trois `pmuludq` par produit), faute
  d'instruction dédiée en AVX2.
- Clang `-O2` ne vectorise pas `sum_if` : comparer des entiers de 64 bits en
  vectoriel demande `pcmpgtq` (SSE4.2), absent du x86-64 de base.
- Un `if` qui protège une **écriture** reste un branchement partout : le compilateur
  ne s'autorise pas à écrire systématiquement à la place du programmeur.

```asm
; chain_xor_mul, gcc-O2 : xor et multiplication sur la même chaîne (rax)
xor    rax, QWORD PTR [rdi]
add    rdi, 0x8
imul   rax, rdx
; split_xor_mul, gcc-O2 : la multiplication porte sur rdx, seul le xor touche rax
mov    rdx, QWORD PTR [rdi]
imul   rdx, rcx
xor    rax, rdx
; sum_if, gcc-scalar : saut conditionnel qui dépend de la donnée
cmp    rax, rcx
jb     <sum_if+0x2b>
add    rdx, rax
```

### 3.2 Modèles et prédictions

**Transparence :** un essai de mise au point du harnais (un processus, un tour
mesuré) a montré pour `filter_copy` de `gcc-scalar` un coût d'environ 6 ns par élément
à $p = 0{,}5$ mélangé, contre 0,4 ns trié. Les prédictions de la partie 2 en tiennent
compte.

**Modèle de pénalité**, fixé à l'avance. Si le prédicteur parie toujours sur la
direction majoritaire, il se trompe sur la part minoritaire des éléments :

$$
m(p) = \min(p,\ 1 - p),
\qquad
c(p) = c_0 + P \cdot m(p).
$$

**Modèle des petites boucles :** $T(n) = a + b\,n$, ajusté sur $n \geq 256$.

Partie 1, dépendances (médianes entre processus) :

1. Dans les binaires où les deux noyaux restent scalaires (`gcc-scalar`, `gcc-O2`,
   `clang-scalar`), $c_{\text{chain}}/c_{\text{split}}$ entre 2,5 et 4,5 : environ
   4 cycles de latence (multiplication et xor) contre 1 (xor).
2. $c$ de `chain_xor_mul` identique dans les 6 binaires, à 15 % près.
3. Vectoriser `split_xor_mul` avec une multiplication émulée : effet incertain,
   rapport scalaire sur vectorisé entre 0,8 et 2,5 (confiance faible).
4. $c_{\text{one}}/c_{\text{four}}$ entre 1,5 et 3,5 dans `gcc-scalar` et
   `clang-scalar` : quatre chaînes d'addition avancent en parallèle.
5. Contrôles : $c_{\text{bis}}/c_{\text{one}}$ entre 0,97 et 1,03 et
   $c_{\text{twice}}/c_{\text{one}}$ entre 1,8 et 2,1 pour chaque binaire.

Partie 2, branchements :

6. **`filter_copy` (branchement partout)** : coût en cloche selon $p$, maximal à
   $p = 0{,}5$ ; $c_{\text{mél}}/c_{\text{trié}} \geq 5$ dans les 6 binaires ;
   $c_{\text{alt}}/c_{\text{trié}}$ entre 0,8 et 1,5, un motif régulier étant
   prévisible.
7. **Pénalité** : ajustée sur les 7 jeux mélangés, $P$ entre 5 et 15 ns, avec
   $R^2 > 0{,}9$.
8. **`sum_if`** : même cloche pour `gcc-scalar` ; pour les 5 autres binaires (`cmov`
   ou masque), coût plat : rapport du maximum au minimum sur les 9 jeux inférieur à
   1,15.
9. **`filter_copy_mask`** : plat dans les 6 binaires (maximum sur minimum inférieur à
   1,15) ; plus rapide que `filter_copy` pour $0{,}1 \leq p \leq 0{,}9$ mélangé ; pas
   plus rapide à $p = 0$, $p = 1$, trié et alterné.

Partie 3, petites boucles :

10. Pour les `sum_one` scalaires, $a$ entre 2 et 15 ns. B1 avait trouvé un surcoût
    d'environ 12 ns par appel à $n = 64$, mais pas à $n = 256$. Prédiction tirée de
    B1 : un écart $e(n)$ d'au moins 3 ns, **localisé** entre $n = 32$ et $n = 128$ et
    absent à $n \geq 256$. Si l'écart apparaissait au-delà d'une taille et
    persistait, l'hypothèse « sortie de boucle mal prédite à partir d'une certaine
    longueur » serait favorisée.

## 4. Code et parties importantes

- [`src/kernels.c`](src/kernels.c) : les huit noyaux, seul fichier dont la
  compilation varie.
- [`src/harness.c`](src/harness.c) : plan de mesure construit avant la première
  mesure ; construction et mélange des jeux de données hors chronométrage ;
  vérification de chaque résultat et de chaque tampon de filtre.
- [`disasm.py`](disasm.py) : analyse statique.
- [`prepare.py`](prepare.py), [`run.sh`](run.sh) : plan des processus, épinglage sur
  le CPU 11.
- [`verify.py`](verify.py) : complétude, épinglage, exactitude, recalcul en Python.
- [`analyze.py`](analyze.py) : résumés, ajustements et figures selon
  [`STYLE_FIGURES.md`](../../STYLE_FIGURES.md).

Nombre d'appels par échantillon : 64 appels sur 65 536 éléments (partie 1), un appel
sur 65 536 éléments (partie 2), $2^{20}/n$ appels (partie 3).

## 5. Commandes

```sh
make check      # correction : autotests des 6 binaires, rejeu Python
make assembly   # analyse statique seule
make quick      # validation de la chaîne
make campaign   # campagne documentée ; refuse d'écraser data/campaign
make analyze    # résumés et figures depuis data/campaign
```

## 6. Vérification de correction, indépendante de la mesure

- `--self-test` : chaque noyau est comparé à une référence écrite dans le harnais,
  pour 9 tailles (dont 0, 1 et des tailles non multiples de 4) et 5 valeurs de $p$ ;
  le contenu des tampons de filtre est vérifié.
- Pendant la campagne, hors chronométrage : chaque résultat est comparé à sa valeur
  attendue, et chaque tampon de filtre au contenu attendu, dans l'ordre.
- `verify.py` : valeurs attendues identiques pour tous les binaires ; avec
  `--replay`, recalcul en Python des parties 1 et 3.

## 7. Protocole de la campagne

- 6 binaires × 15 processus indépendants = 90 processus, ordre aléatoire fixé
  (graine `20260917`), épinglés sur le CPU 11.
- 21 tours par processus, le premier déclaré échauffement ; dans chaque tour, les
  53 mesures dans un ordre tiré au hasard.
- Unité statistique : le processus ; dans un processus, médiane sur 20 tours de $c$
  (parties 1 et 2) ou de $T(n)$ (partie 3).
- Entre processus : médiane et IC 95 % bootstrap percentile (10 000 tirages).
- Rapports (prédictions 1 à 6, 8, 9) : calculés par processus, puis résumés.
- Modèle de pénalité (7) : moindres carrés sur les médianes entre processus des
  7 jeux mélangés.
- Petites boucles (10) : droite ajustée par moindres carrés sur $n$ = 256, 384, 512,
  768 et 1 024.
- Aucun réglage global de la machine.

## 8. Données brutes

- [`data/campaign/`](data/campaign/) : `plan.csv` (écrit avant la mesure),
  `topology.csv`, un fichier `run-NNN.csv` par processus (une ligne par échantillon :
  partie, mesure, jeu de données, taille, appels, durée, CPU, résultat, valeur
  attendue, validité du tampon) et `run-NNN-meta.csv`.
- [`data/environment-campaign.txt`](data/environment-campaign.txt) : machine,
  versions, commandes de compilation, empreintes SHA-256 des sources et binaires.
- [`reports/assembly.csv`](reports/assembly.csv), [`reports/asm/`](reports/asm/) :
  analyse statique.
- Résumés : `reports/campaign-dependencies.csv`, `-branches.csv`,
  `-branch-summary.csv` (rapports, ajustement de la pénalité), `-small.csv`,
  `-rusage.csv`.

Les 100 170 échantillons (90 processus × 21 tours × 53 mesures) ont tous un résultat
exact et, pour les filtres, un tampon exact. Aucune observation retirée.

## 9. Figures

- [`figures/campaign-dependencies.pdf`](figures/campaign-dependencies.pdf) : $c$ des
  quatre noyaux de dépendance pour GCC (a) et Clang (b) ; rapports par processus
  $c_{\text{chain}}/c_{\text{split}}$ (c) et $c_{\text{one}}/c_{\text{four}}$ (d).
- [`figures/campaign-branches.pdf`](figures/campaign-branches.pdf) : $c$ selon $p$
  pour `sum_if`, `filter_copy` et `filter_copy_mask`, GCC en haut, Clang en bas ;
  carrés : jeu trié ; croix : jeu alterné.
- [`figures/campaign-small.pdf`](figures/campaign-small.pdf) : $T(n)$ de `sum_one`
  (a, b) et écart $e(n)$ à la droite ajustée sur $n \geq 256$ (c, d).

## 10. Résultats observés et interprétation

Chiffres de la campagne, **sur le CPU 11 de cette machine** ; médianes entre
15 processus.

### 10.1 Dépendances : la place d'une instruction compte plus que leur nombre

| Binaire | `chain_xor_mul` | `split_xor_mul` | `sum_one` | `sum_four` | $c_{\text{chain}}/c_{\text{split}}$ | $c_{\text{one}}/c_{\text{four}}$ |
|---|---:|---:|---:|---:|---:|---:|
| gcc-scalar | 1,614 | 0,539 | 0,406 | 0,269 | 3,00 | 1,50 |
| gcc-O2 | 1,618 | 0,542 | 0,405 | 0,139 | 2,99 | 2,92 |
| gcc-O3-v3 | 1,616 | 0,309 | 0,120 | 0,152 | 5,22 | 0,79 |
| clang-scalar | 1,611 | 0,404 | 0,403 | 0,265 | 3,98 | 1,52 |
| clang-O2 | 1,644 | 0,589 | 0,138 | 0,269 | 2,80 | 0,51 |
| clang-O3-v3 | 1,615 | 0,310 | 0,093 | 0,135 | 5,23 | 0,69 |

(Les quatre premières colonnes donnent $c$ en ns ; les rapports sont des médianes des
rapports par processus.)

- **Mêmes opérations, trois fois plus lent** : `chain_xor_mul` coûte 3,0 fois
  `split_xor_mul` dans les deux binaires GCC scalaires, uniquement parce que la
  multiplication se trouve sur la chaîne qui relie les itérations. Prédiction 1
  confirmée (3,00 ; 2,99 ; 3,98).
- **Une dépendance résiste à tout le reste** : `chain_xor_mul` coûte 1,61 à 1,64 ns
  dans les 6 binaires, vectorisés ou non. Prédiction 2 confirmée.
- Clang scalaire obtient `split_xor_mul` à 0,404 ns contre 0,539 ns pour GCC : en
  déroulant la boucle par 4, il regroupe les xor en arbre, ce qui raccourcit encore
  la chaîne.
- Vectoriser `split_xor_mul` aide avec AVX2 (1,75 fois chez GCC, 1,30 fois chez Clang)
  mais **ralentit** en SSE2 : Clang -O2 est 1,46 fois plus lent que Clang scalaire.
  Prédiction 3 partiellement réfutée : la vectorisation automatique, avec une
  multiplication de 64 bits émulée, n'est pas toujours un gain.
- Quatre accumulateurs scalaires sont 1,50 et 1,52 fois plus rapides qu'un seul.
  Prédiction 4 confirmée, à la borne basse : quatre chaînes indépendantes ne donnent
  pas quatre fois le débit.
- Contrôles : $c_{\text{twice}}/c_{\text{one}}$ de 1,936 à 2,049 ;
  $c_{\text{bis}}/c_{\text{one}}$ de 0,969 à 1,015 par processus. Prédiction 5
  confirmée en médiane ; un seul processus sur 90 tombe à 0,969, juste sous la borne
  de 0,97.

**Lecture exploratoire, en cycles.** Si un cycle dure environ 0,40 ns (soit 2,5 GHz,
la valeur de `scaling_cur_freq` relevée en B1), plusieurs coûts deviennent des
nombres entiers de cycles de latence : `sum_one` scalaire, 1,0 cycle par élément (une
addition) ; `chain_xor_mul`, 4,0 cycles (xor et multiplication de 3 cycles) ;
`sum_if` avec `cmov` chez GCC -O2, 2,0 cycles (`lea` puis `cmov`) ; sommes AVX2 à
4 voies, environ un quart de cycle. Ce modèle est **cohérent sans être prouvé** : il
n'explique ni `split_xor_mul` scalaire (1,35 cycle au lieu de 1), ni `sum_four`
(0,66 au lieu de 0,25), ni la boucle vide de B1 (0,203 ns, un demi-cycle). Seul un
compteur de cycles trancherait.

### 10.2 Branchements : mêmes données, 14 fois plus lent

| Binaire | $c_{\text{mél}}/c_{\text{trié}}$ de `filter_copy` | $c_{\text{alt}}/c_{\text{trié}}$ | Pénalité ajustée $P$ | $R^2$ |
|---|---:|---:|---:|---:|
| gcc-scalar | 13,9 | 1,00 | 10,9 ns | 0,94 |
| gcc-O2 | 14,0 | 0,99 | 10,9 ns | 0,94 |
| gcc-O3-v3 | 14,0 | 0,99 | 10,9 ns | 0,94 |
| clang-scalar | 14,6 | 0,90 | 9,4 ns | 0,99 |
| clang-O2 | 14,5 | 0,89 | 9,5 ns | 0,99 |
| clang-O3-v3 | 16,6 | 1,00 | 9,8 ns | 1,00 |

- **Le même ensemble de valeurs**, traité par le même code machine, coûte 5,7 ns par
  élément mélangé et 0,41 ns trié (GCC). Seule change la prévisibilité de la
  condition. Un motif régulier (alterné) est aussi bien prédit que l'ordre trié.
  Prédiction 6 confirmée.
- **Pénalité** : $P$ vaut 9,4 à 10,9 ns par mauvaise prédiction ; prédiction 7
  confirmée (intervalle 5 à 15 ns, $R^2 \geq 0{,}94$).
- **Le modèle « parier sur la majorité » sous-estime pourtant le coût** aux $p$
  intermédiaires. Avec la pénalité tirée de $p = 0{,}5$ (10,6 ns chez GCC), le coût
  observé à $p = 0{,}1$ impliquerait $m = 18$ % de mauvaises prédictions au lieu de
  10 %, et 35 % au lieu de 25 % à $p = 0{,}25$. Hypothèse : le prédicteur s'appuie
  sur l'historique récent, qui n'apporte aucune information sur des données
  indépendantes, et se trompe plus souvent qu'un simple vote majoritaire. Non
  vérifiable sans compteur.
- **`sum_if` dépend du compilateur** : cloche de 14 pour `gcc-scalar`, coût plat pour
  les 5 autres binaires (écart maximal entre jeux de 1,8 %). Prédiction 8 confirmée.
  Le `cmov` de GCC -O2 coûte 0,80 ns partout : deux fois le branchement bien prédit
  (0,40 ns), mais 7 fois moins que le branchement imprévisible.
- **`filter_copy_mask`** reste plat (0,41 à 0,45 ns, écart maximal 8 %), 13 fois plus
  rapide que `filter_copy` à $p = 0{,}5$ mélangé, et légèrement plus lent que lui
  quand la condition est prévisible ($p = 0$ : 0,415 contre 0,403 ns chez GCC ;
  0,413 contre 0,303 ns chez Clang). Prédiction 9 confirmée.
- **Seuil de rentabilité.** La version sans branchement l'emporte dès que le taux de
  mauvaises prédictions dépasse l'écart de coût à $p = 0$ divisé par la pénalité :

  $$
  m^\ast = \frac{c_{\text{mask}}(0) - c_{\text{if}}(0)}{P}
  \approx \frac{0{,}415 - 0{,}403}{10{,}9} \approx 0{,}1\ \%\ \text{(GCC)},
  \qquad
  \frac{0{,}413 - 0{,}303}{9{,}4} \approx 1{,}2\ \%\ \text{(Clang)},
  $$

  où $c_{\text{mask}}$ et $c_{\text{if}}$ sont les coûts de `filter_copy_mask` et de
  `filter_copy`.

### 10.3 Petites boucles : la sortie de boucle mal prédite, retrouvée

On lit ici le **coût marginal** $\Delta T/\Delta n$ entre deux tailles successives.

- **GCC scalaire et -O2** (même code machine) : 0,40 ns par élément supplémentaire
  de $n = 1$ à $n = 32$, puis **un saut de 17,5 ns entre 32 et 48 éléments** (6,5 ns
  attendus), soit un excédent d'environ 11 ns : la pénalité mesurée indépendamment en
  10.2. Interprétation : jusqu'à environ 32 itérations, le prédicteur anticipe la
  sortie de boucle ; au-delà, il se trompe une fois par appel. C'est l'explication du
  surcoût d'environ 12 ns par appel observé en B1 à $n = 64$.
- Entre 48 et 192 éléments, le coût marginal tombe à 0,27 à 0,34 ns, puis revient à
  0,40 ns ; ce déficit cumulé (environ 13 ns) compense le saut, et à partir de
  256 éléments la durée suit la droite $T(n) = 0{,}406\,n - 1{,}1$ ns. **Nous
  n'expliquons pas cette compensation.**
- Prédiction 10 : critère rempli pour les deux binaires GCC scalaires ($e(n)$ vaut
  14,3 ; 12,0 ; 8,9 ; 5,0 ns de 48 à 128 éléments, moins de 0,6 ns au-delà), mais sous
  la forme d'un saut suivi d'une compensation, pas d'une bosse isolée. **Non rempli
  pour Clang scalaire** : aucun saut, un coût marginal d'environ 0,1 à 0,27 ns entre
  16 et 128 éléments, puis 0,40 ns ; la droite ajustée à partir de 256 éléments n'y
  décrit pas les petites tailles. Hypothèse pour ces appels très courts : les chaînes
  de deux appels successifs sont indépendantes et peuvent progresser en même temps
  dans la fenêtre d'exécution dans le désordre.
- Les binaires vectorisés atteignent 0,08 à 0,13 ns par élément supplémentaire
  au-delà de 256 éléments, environ un quart du coût scalaire.

### 10.4 Ce que B2 permet et ne permet pas de conclure

Permet de conclure, sur cette machine :

- à opérations identiques, placer une multiplication sur la dépendance entre
  itérations multiplie le coût par 3 à 5 et empêche la vectorisation ;
- un branchement imprévisible coûte environ 10 ns par mauvaise prédiction, soit
  jusqu'à 14 fois le coût d'un élément bien prédit ;
- qu'une condition devienne branchement, `cmov` ou masque dépend du compilateur et
  des options ; seule une écriture conditionnelle garde toujours un branchement ;
- une version sans branchement est plus lente de 3 % (GCC) à 36 % (Clang) quand la
  condition est prévisible, et jusqu'à 13 fois plus rapide sinon.

Ne permet pas de conclure :

- le nombre de mauvaises prédictions ni la durée d'un cycle : ils sont déduits de
  durées sous hypothèses, pas comptés ;
- que ces valeurs s'appliquent à un autre processeur ou à des données réelles, dont
  les motifs sont rarement indépendants ;
- la cause de la compensation après la sortie mal prédite, ni celle du faible coût
  des appels courts chez Clang.

Pour les 13 ms : à 10 ns par mauvaise prédiction, il en faudrait plus d'un million
pour atteindre 13 ms. Ces effets peuvent peser sur un chemin de code chargé, mais ne
suffisent pas, seuls, à expliquer une requête localhost de cet ordre, sauf à exécuter
des millions de branchements imprévisibles : ce sera à vérifier dans le code
d'origine, pas à supposer.

## 11. Limites et expériences suivantes

- Un seul CPU logique (11), une campagne (74 s de mesure, charge moyenne sur une
  minute de 0,72 au début), jusqu'à 38 changements de contexte involontaires par
  processus.
- Aucun compteur matériel : mauvaises prédictions et cycles sont inférés.
- Données synthétiques : conditions indépendantes et uniformes, rarement le cas en
  pratique.
- Heuristique de détection des branchements imparfaite ; classification des noyaux
  conditionnels vérifiée à la main.
- `clang-scalar` n'interdit pas les `cmov` : la comparaison « branchement contre sans
  branchement » pour `sum_if` ne repose que sur GCC.

Expériences suivantes :

1. **C1, parcours mémoire** : localité, lignes de cache et bande passante, pour
   expliquer la convergence des débits au-delà de 2 Mio observée en B1.
2. Avec votre accord seulement (réglage global) : abaisser temporairement
   `perf_event_paranoid` et compter `branch-misses` et `cycles`, pour valider ou
   réfuter les inférences des sections 10.1 à 10.3.
3. Petites boucles : faire varier $n$ d'un appel à l'autre (tailles aléatoires entre
   1 et 64) pour vérifier que le saut entre 32 et 48 éléments disparaît quand aucune
   longueur n'est prévisible, et qu'un surcoût apparaît dès les petites tailles.

## 12. Compréhension et prolongement

Questions :

1. `chain_xor_mul` et `split_xor_mul` exécutent les mêmes instructions. Pourquoi
   l'une est-elle trois fois plus lente, et pourquoi aucun compilateur ne peut-il
   vectoriser la première ?
2. Pourquoi le jeu trié et le jeu alterné coûtent-ils autant l'un que l'autre, alors
   qu'ils sont très différents ?
3. Pourquoi `sum_if` n'est-il sensible à l'ordre des données qu'avec `gcc-scalar`, et
   que faut-il donc toujours préciser en présentant une mesure de branchement ?
4. Dans quel cas `filter_copy_mask` est-il le mauvais choix, et comment le seuil de
   rentabilité $m^\ast$ se calcule-t-il à partir de ces mesures ?
5. Qu'est-ce qui, dans la partie 3, relie le surcoût de B1 à $n = 64$ à la pénalité
   mesurée en partie 2, et quelle expérience le confirmerait directement ?

Prolongement : écrire une version de `filter_copy` pour des données **triées par
blocs** (par exemple 64 éléments retenus, puis 64 non retenus). Prédire, avant de
mesurer, $c$ pour des blocs de 1, 4, 16, 64 et 256 éléments, puis mesurer et comparer
à la pénalité $P$ d'environ 10 ns.
