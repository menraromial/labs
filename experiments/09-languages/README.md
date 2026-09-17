# E1 - Comparaison entre langages : C, Rust, Go et Python à travail équivalent

## 1. Question et prérequis

**Question :** à travail strictement équivalent (mêmes données, même algorithme, mêmes
types et même résultat), que coûte le même calcul écrit en C, Rust, Go et Python ? Et
que change l'écriture idiomatique de chaque langage, y compris le recours à une
bibliothèque native comme NumPy ?

Prérequis : [B1](../03-compilation/README.md) et [B2](../04-dependencies-branches/README.md)
(lire l'assembleur, chaîne de dépendance, vérifications et branchements),
[C1](../05-memory-traversal/README.md) (coût d'un accès mémoire) et
[A2](../02-microbenchmark/README.md) (protocole : processus indépendants, contrôles A/A et
positif). E1 porte sur le **régime établi** ; le démarrage n'est mesuré ici que pour le
séparer du reste, et sera étudié en E2.

## 2. Notions nécessaires

**Intuition.** Comparer deux langages, c'est comme comparer deux cuisiniers : il faut la
même recette, les mêmes ingrédients et le même plat à la fin. Sinon on compare des
recettes, pas des cuisiniers. Et un cuisinier qui fait livrer un plat tout prêt
(une bibliothèque native) ne dit rien de sa propre vitesse.

- **Compilation anticipée** (*ahead-of-time compilation*) : C, Rust et Go traduisent le
  programme en code machine avant l'exécution ; GCC, `rustc` (LLVM) et le compilateur
  de Go n'optimisent pas de la même façon.
- **Interpréteur** (*interpreter*) : CPython exécute un code intermédiaire (*bytecode*)
  instruction par instruction ; chaque opération sur un entier ou un flottant manipule
  un objet. CPython 3.14 spécialise ses instructions selon les types rencontrés
  (*specializing adaptive interpreter*) ; son **JIT** (*just-in-time compiler*)
  expérimental est présent mais **désactivé** ici.
- **Ramasse-miettes** (*garbage collector*, GC) : récupération automatique de la
  mémoire. Go en possède un ; CPython compte les références et ajoute un ramasse-miettes
  pour les cycles ; C et Rust n'en ont pas.
- **Vérification de bornes** (*bounds check*) : test, avant l'accès `a[i]`, que `i` est
  dans le tableau. Rust et Go l'imposent, mais leur compilateur peut l'éliminer ou la
  sortir de la boucle quand il prouve qu'elle réussit toujours.
- **Débordement entier** (*integer overflow*) : en C, Rust (`wrapping_mul`) et Go, un
  produit de deux entiers de 64 bits est réduit modulo $2^{64}$ ; en Python, les entiers
  grandissent sans limite, et la réduction doit être écrite (`& MASK`).
- **Bibliothèque native** (*native library*) : code compilé appelé depuis Python (NumPy,
  OpenBLAS). Son coût dépend de cette bibliothèque, pas du langage appelant.
- **Arrondi flottant** : le résultat d'une somme de flottants dépend de l'ordre des
  additions. Une somme **stricte** additionne de gauche à droite ; OpenBLAS regroupe
  les termes, et `math.sumprod` calcule produits et sommes en précision étendue.

### Notations

**Versions mesurées** (colonne `build`) :

| Version | Chaîne | Options |
|---|---|---|
| `c-O2` | GCC 15.2 | `-O2 -std=c17` |
| `c-O3` | GCC 15.2 | `-O3 -std=c17` : sépare l'effet du niveau d'optimisation de celui du langage |
| `rust` | `rustc` 1.85 (LLVM 19) | `-C opt-level=3`, bibliothèque standard seule |
| `go` | Go 1.26 | `go build`, `GOAMD64=v1`, bibliothèque standard seule |
| `python` | CPython 3.14.4, NumPy 2.3.5 (OpenBLAS) | JIT désactivé, `OPENBLAS_NUM_THREADS=1` |

Aucune version n'utilise `-march=native` : toutes restent sur le jeu d'instructions
x86-64 de base, sans instruction de fusion multiplication-addition.

**Données.** Un fichier de $2^{22}$ entiers $u_i$ de 64 bits, générés une fois par
SplitMix64 (graine `20260922`) et lus par toutes les versions. $K$ est la constante
impaire `0x9e3779b97f4a7c15` et $\oplus$ le ou exclusif.

**Charges** (colonne `workload`) :

| Charge | Éléments | Calcul | Résultat vérifié |
|---|---:|---|---|
| `hash_chain` | $n = 2^{20}$ | $h \leftarrow (h \oplus u_i) \times K \bmod 2^{64}$, à partir de $h = 0$ | $h$, entier exact |
| `dot` | $n = 2^{20}$ | $s \leftarrow s + a_i\,b_i$, avec $a_i = \lfloor u_i / 2^{11} \rfloor \cdot 2^{-53}$ et $b_i$ de même sur $u_{n+i}$ | $s$, flottant de 64 bits |
| `count` | $n = 2^{22}$ | nombre d'occurrences de chaque clé $k_i = \lfloor \lfloor u_i/2^{48} \rfloor \cdot (\lfloor u_i/2^{32} \rfloor \bmod 2^{16}) / 2^{16} \rfloor$, entre 0 et 65 535 | somme de contrôle $\sum_k c_k \cdot ((k+1)K \bmod 2^{64}) \bmod 2^{64}$ |

`hash_chain` est un calcul entier dont chaque itération dépend de la précédente (voir
B2) ; `dot` un calcul flottant ; `count` un traitement de données par table de
hachage.

**Variantes** (colonne `variant`) :

| Variante | Définition | Versions |
|---|---|---|
| `control` | **traduction contrôlée** : même boucle indexée `for i in 0..n`, même table à adressage ouvert pour `count` ($2^{17}$ cases, sondage linéaire, remise à zéro hors chronométrage) | toutes |
| `control_bis` | identique à `control` sur `hash_chain` | toutes : contrôle A/A |
| `control_double` | deux passes de `hash_chain`, la seconde repartant du $h$ de la première | toutes : contrôle positif, durée attendue × 2 |
| `idiomatic` | **écriture idiomatique** : `hash_chain` par itérateur (`fold` en Rust, `range` en Go, `for x in u` en Python) ; `dot` par itérateur (Rust `zip`, Go `range`) ou `math.sumprod` (Python) ; `count` par `HashMap` (Rust), `map` (Go) ou `collections.Counter` (Python), créée dans la fenêtre chronométrée | Rust, Go, Python |
| `idiomatic_bis` | identique à `idiomatic` sur `count` | Rust, Go, Python : contrôle A/A des structures allouées |
| `numpy` | bibliothèque native : `np.dot` pour `dot`, `np.bincount` pour `count` (clés denses de 0 à 65 535) | Python |

C n'a pas de variante idiomatique : sa bibliothèque standard n'offre ni itérateur ni
table de hachage, et la version contrôlée est l'écriture naturelle.

**Symboles :**

| Symbole | Signification | Unité |
|---|---|---|
| $T$ | durée d'un échantillon (une exécution complète d'une charge) | ns |
| $t$ | coût par élément : $t = T/n$ ; dans un processus, médiane des tours mesurés | ns |
| $\tilde t_v$ | médiane de $t$ entre les 10 processus d'une version $v$ | ns |
| $R_v = \tilde t_v / \tilde t_{\text{c-O2}}$ | rapport d'une version à C `-O2`, même charge et variante `control` | |
| $t_{\text{idiom}}/t_{\text{control}}$ | rapport de l'écriture idiomatique à la traduction contrôlée, par processus | |
| $T_{\text{bis}}/T$, $T_{\text{double}}/T$ | contrôles A/A et positif, par processus | |
| $D$ | durée de démarrage : du lancement (`posix_spawn`) à la fin (`wait4`) d'une commande qui se termine aussitôt | ms |
| $\rho_0$ | rapport du premier tour (échauffement) à la médiane des tours mesurés, par processus | |

Ce qui est **garanti** : l'égalité des résultats (vérifiée, exacte sauf pour
`math.sumprod` et `np.dot`, voir section 6). Ce qui **dépend des chaînes de
compilation et des environnements d'exécution** : le code machine produit, les
vérifications de bornes gardées, le coût de l'interprétation, des tables de hachage et
du démarrage. Ce qui **dépend de la machine** : le coût des instructions restantes.

## 3. Analyse statique et prédictions, écrites avant la campagne

### 3.1 Ce que montre l'assembleur

[`disasm.py`](disasm.py) extrait les fonctions mesurées des trois binaires compilés
([`reports/assembly.csv`](reports/assembly.csv), extraits dans
[`reports/asm/`](reports/asm/)) ; les vérifications de bornes ont été relues à la main.

| Fonction | `c-O2` | `c-O3` | `rust` | `go` |
|---|---|---|---|---|
| `hash_chain`, contrôlée | 1 `xor` et 1 `imul` par élément | identique | identique, déroulée par 4, aucune vérification | identique, aucune vérification, constante rechargée à chaque tour |
| `hash_chain`, idiomatique | sans objet | sans objet | identique à la contrôlée | identique à la contrôlée |
| `dot`, contrôlée | `mulsd` puis `addsd` scalaires | produits vectorisés (`mulpd`), sommes scalaires dans l'ordre | scalaire, déroulée par 4, vérification sortie de la boucle | scalaire, **une vérification de bornes par élément** |
| `dot`, idiomatique | sans objet | sans objet | identique, sans vérification | identique à la contrôlée |
| `count`, contrôlée | sondage et incrément, sans vérification | identique | **2 vérifications de bornes par élément** | **2 à 3 vérifications de bornes par élément** |

Dans les trois compilés, `hash_chain` et `dot` gardent une chaîne de dépendance d'une
itération à l'autre (`imul` pour l'entier, `addsd` pour le flottant, voir B2). Aucun
compilateur ne peut la raccourcir sans changer le résultat : l'ordre des additions
flottantes est imposé, et `c-O3` ne vectorise que les produits.

### 3.2 Transparence

Avant d'écrire ce qui suit :

- B2 a mesuré 1,61 ns par élément pour la même chaîne entière (`chain_xor_mul`) en C
  sur le CPU 11 : la prédiction 1 en est directement tirée.
- `make check` (données réduites 256 fois) a montré, en affichant le début du fichier de
  démarrage, **deux** durées de démarrage : 0,58 ms pour `c-O3` et 19,5 ms pour
  `python`. Aucune autre durée n'a été lue.
- Un essai de dimensionnement à pleine échelle (2 tours) a donné la durée totale de
  chaque processus (0,11 s pour `c-O2`, 0,40 s pour `rust`, 0,48 s pour `go`, 9,1 s
  pour `python`) et la mémoire maximale de Python (585 Mio).
- Les résultats de `check` ont montré que `math.sumprod` et `np.dot` diffèrent de la
  somme stricte dans les derniers bits : ce fait est traité comme une condition de
  validité (section 6), pas comme une prédiction.

### 3.3 Prédictions

Toutes les prédictions portent sur le CPU 11 (cœur P), en médianes entre processus.

Comparaison contrôlée, versions compilées :

1. `hash_chain` : $\tilde t_{\text{c-O2}}$ entre 1,4 et 1,8 ns ; $R_v$ entre 0,9 et 1,15
   pour `c-O3`, `rust` et `go` : la chaîne `xor` puis `imul` fixe la vitesse, quel que
   soit le reste de la boucle.
2. `dot` : $\tilde t_{\text{c-O2}}$ entre 1,0 et 1,8 ns ; $R_v$ entre 0,9 et 1,15 pour
   `c-O3`, `rust` et `go`, malgré la vérification de bornes de Go (toujours bien
   prédite).
3. `count` : $\tilde t_{\text{c-O2}}$ entre 2 et 6 ns ; $R_v$ entre 0,9 et 1,1 pour
   `c-O3`, entre 1,0 et 1,3 pour `rust` et entre 1,0 et 1,5 pour `go` (vérifications de
   bornes dans la boucle).

Comparaison contrôlée, Python :

4. `hash_chain` : 100 à 400 ns par élément, soit $R_{\text{python}}$ entre 60 et 250 ;
   `dot` : 50 à 150 ns ; `count` : 400 à 1 500 ns.

Écritures idiomatiques :

5. Rust et Go : $t_{\text{idiom}}/t_{\text{control}}$ entre 0,95 et 1,05 pour
   `hash_chain` et `dot` (même code machine, ou presque).
6. Python : `for x in u` entre 0,6 et 0,9 fois la boucle indexée ; `math.sumprod` entre
   2 et 15 ns par élément.
7. `count` : `HashMap` de Rust (fonction de hachage SipHash) entre 10 et 30 ns par
   élément ; `map` de Go entre 8 et 25 ns ; `collections.Counter` entre 30 et 80 ns.

Bibliothèque native :

8. `np.dot` : 0,15 à 0,6 ns par élément, **plus rapide que la boucle stricte de C** d'un
   facteur 2 à 8 : OpenBLAS n'additionne pas dans l'ordre et peut donc vectoriser la
   somme. `np.bincount` : 0,5 à 3 ns par élément.

Contrôles et environnement d'exécution :

9. $T_{\text{bis}}/T$ entre 0,97 et 1,03 par processus pour C, Rust et Go, entre 0,95
   et 1,05 pour Python et pour `idiomatic_bis` ; $T_{\text{double}}/T$ entre 1,8 et
   2,2.
10. Aucune collecte automatique du ramasse-miettes pendant un échantillon, en Go comme
    en Python.
11. $\rho_0 \leq 1{,}3$ pour toutes les versions : le premier tour n'est pas beaucoup plus
    lent que le régime établi.
12. Démarrage $D$ (médianes) : 0,3 à 1,5 ms pour C et Rust ; 0,5 à 3 ms pour Go ; 10 à
    40 ms pour Python ; 50 à 200 ms pour Python avec `import numpy`.

## 4. Code et parties importantes

- [`src/c/bench.c`](src/c/bench.c), [`src/rust/bench.rs`](src/rust/bench.rs),
  [`src/go/bench.go`](src/go/bench.go), [`src/python/bench.py`](src/python/bench.py) :
  une version par langage, **même structure** : lecture du fichier d'entrée, dérivation
  des données hors chronométrage, plan des mesures mélangé à chaque tour par le même
  générateur (xorshift), chronométrage de chaque échantillon par l'horloge monotone du
  langage (`clock_gettime`, `Instant`, `time.Now`, `time.perf_counter_ns`), résultat
  et CPU enregistrés, écriture du CSV après la dernière mesure.
- Les fonctions mesurées sont marquées « jamais intégrées » en C, Rust et Go
  (`noinline`, `#[inline(never)]`, `//go:noinline`), pour lire leur assembleur et
  garder le même périmètre.
- Go : `runtime.GC()` et Python : `gc.collect()` sont appelés **avant** chaque
  échantillon, hors chronométrage, pour que les déchets des échantillons précédents ne
  soient pas collectés pendant la mesure ; le nombre de collectes pendant chaque
  échantillon est enregistré.
- [`src/c/launch.c`](src/c/launch.c) : mesure du démarrage, commandes lancées dans un
  ordre tiré au hasard à chaque répétition.
- [`disasm.py`](disasm.py) : analyse statique ; [`prepare.py`](prepare.py),
  [`run.sh`](run.sh) : plan et exécution épinglée ; [`verify.py`](verify.py) :
  vérifications ; [`analyze.py`](analyze.py) : résumés et figures selon
  [`STYLE_FIGURES.md`](../../STYLE_FIGURES.md).

## 5. Commandes

```sh
make assembly   # analyse statique des trois versions compilées
make check      # correction : données réduites, résultats recalculés en Python
make quick      # validation de la chaîne (1 processus par version, 3 tours)
make campaign   # campagne documentée ; refuse d'écraser data/campaign
make analyze    # résumés et figures depuis data/campaign
```

## 6. Vérification de correction, indépendante de la mesure

- `verify.py` recalcule en Python, à partir du fichier d'entrée, la chaîne de hachage
  (une et deux passes), la somme stricte des produits et la somme de contrôle des
  occurrences (par `np.bincount`), puis compare **chaque** échantillon de chaque
  version.
- `dot` : les boucles strictes de C, Rust et Go (contrôlées et idiomatiques) et la
  boucle contrôlée de Python doivent donner **exactement** le même flottant ;
  `math.sumprod` et `np.dot` doivent en être à moins de $10^{-12}$ en valeur relative.
- La somme des clés dérivées par chaque version est comparée à celle recalculée ;
  l'empreinte SHA-256 du fichier d'entrée est contrôlée ; tous les échantillons doivent
  avoir été pris sur le CPU prévu ; le JIT de Python doit être désactivé.
- Démarrage : chaque commande doit s'être terminée avec le code 0.
- Un essai de mutation (un bit d'un résultat de `dot` modifié) a bien fait échouer la
  vérification.

## 7. Protocole de la campagne

- 5 versions × 10 processus indépendants = 50 processus, ordre aléatoire fixé (graine
  `20260922`), tous épinglés sur le CPU 11 ; `OPENBLAS_NUM_THREADS=1` pour ces seuls
  processus.
- 11 tours par processus, le premier déclaré échauffement ; dans chaque tour, toutes
  les mesures de la version dans un ordre tiré au hasard.
- Unité statistique : le processus. $t$ est la médiane des 10 tours mesurés ; entre
  processus, médiane et IC 95 % bootstrap percentile (10 000 tirages).
- Rapports entre variantes d'une même version ($t_{\text{idiom}}/t_{\text{control}}$,
  contrôles, $\rho_0$) : par processus, puis résumés.
- Rapports entre versions ($R_v$) : les processus diffèrent d'une version à l'autre ;
  rapport des médianes de deux groupes indépendants, IC 95 % par bootstrap de chaque
  groupe.
- Démarrage : 50 répétitions de chaque commande, dans un ordre tiré au hasard à chaque
  répétition, lancées depuis le CPU 11 ; médiane et IC 95 % bootstrap sur les
  répétitions.
- Aucun réglage global de la machine.

## 8. Données brutes

- [`data/campaign/`](data/campaign/) : `plan.csv` (écrit avant la mesure), un fichier
  `run-NNN.csv` par processus (une ligne par échantillon : version, tour, position,
  charge, variante, éléments, passes, durée, résultat, collectes du ramasse-miettes
  pendant l'échantillon, CPU avant et après), `run-NNN-meta.csv` (environnement
  d'exécution, mémoire maximale, somme des clés, collectes automatiques, état du JIT et
  du GIL), `startup.csv` (chaque démarrage) et `input.sha256` (empreinte du fichier
  d'entrée, régénérable par `make`).
- [`data/environment-campaign.txt`](data/environment-campaign.txt) : machine, versions
  de GCC, `rustc`, Go, CPython et NumPy, bibliothèque BLAS, options de compilation,
  empreintes SHA-256 des sources et des binaires.
- [`reports/assembly.csv`](reports/assembly.csv), [`reports/asm/`](reports/asm/) :
  analyse statique.
- Résumés : `reports/campaign-costs.csv` ($\tilde t$ par version, charge et variante),
  `-between-builds.csv` ($R_v$), `-within-process.csv` (rapports entre variantes et
  contrôles), `-warmup.csv` ($\rho_0$), `-meta.csv`, `-startup.csv`.

La campagne a duré 8 min, avec une charge moyenne de 3,54 au départ, plus élevée que
pour les projets précédents. Les 4 290 échantillons des 50 processus ont un résultat
exact, et les 300 démarrages se sont terminés normalement. Aucune observation retirée.

## 9. Figures

- [`figures/campaign-steady.pdf`](figures/campaign-steady.pdf) : coût par élément $t$ de
  chaque version pour la chaîne de hachage (a), le produit scalaire (b) et le comptage
  (c), un point par processus ; bleu : traduction contrôlée, orange : écriture
  idiomatique, vert : NumPy ; trait noir : médiane et IC 95 %.
- [`figures/campaign-startup.pdf`](figures/campaign-startup.pdf) : durée de démarrage
  $D$ de chaque commande, un point par répétition (a) ; mémoire résidente maximale
  médiane d'un processus de mesure (b).

Les axes verticaux de la première figure et du panneau (a) de la seconde sont
logarithmiques : deux graduations également espacées y représentent un même facteur.

## 10. Résultats observés et interprétation

Médianes entre 10 processus par version, CPU 11.

### 10.1 Comparaison contrôlée : les trois langages compilés font jeu égal

| $\tilde t$ en ns par élément | `c-O2` | `c-O3` | `rust` | `go` | `python` |
|---|---:|---:|---:|---:|---:|
| `hash_chain` | 1,90 | 1,90 | 1,84 | 1,91 | 131 |
| `dot` | 1,50 | 1,69 | 1,48 | 1,51 | 44,9 |
| `count` | 3,45 | 3,50 | 3,59 | 3,58 | 270 |

| $R_v$ (IC 95 %) | `c-O3` | `rust` | `go` | `python` |
|---|---:|---:|---:|---:|
| `hash_chain` | 0,998 [0,956 ; 1,044] | 0,971 [0,938 ; 0,997] | 1,006 [0,972 ; 1,040] | 69,2 [66,9 ; 71,1] |
| `dot` | 1,120 [1,077 ; 1,165] | 0,986 [0,937 ; 1,021] | 1,002 [0,970 ; 1,037] | 29,8 [28,9 ; 30,8] |
| `count` | 1,015 [0,968 ; 1,046] | 1,040 [0,998 ; 1,071] | 1,036 [0,994 ; 1,064] | 78,3 [75,0 ; 80,7] |

- **À travail équivalent, C, Rust et Go coûtent la même chose à 4 % près** sur les trois
  charges. Prédictions 1 à 3 confirmées pour les rapports ; les vérifications de bornes
  de Rust et de Go dans la table (section 3.1) coûtent au plus 4 %, un écart dont
  l'intervalle contient 1.
- **Prédiction 1 réfutée pour la valeur absolue** : `hash_chain` coûte 1,90 ns en C,
  au-dessus de la borne de 1,8 ns tirée de B2 (1,61 ns pour la même chaîne). Deux
  différences, non départagées : ici 8 Mio de données lues en séquence contre 512 Kio
  tenant dans le cache L2 en B2 (C1 a mesuré une hausse du coût séquentiel entre ces
  tailles), et une charge moyenne de 3,54 contre 0,72.
- **`-O3` n'est pas toujours meilleur** : pour `dot`, `c-O3` est 1,12 fois plus lent que
  `c-O2`. GCC y vectorise les produits par paires (`mulpd`) mais doit garder les
  additions dans l'ordre ; ce découpage ne raccourcit pas la chaîne d'additions et
  coûte ici davantage. L'origine exacte du surcoût n'est pas établie.
- **Python contrôlé coûte 30 à 78 fois C**, et l'écart dépend de la charge : 30 fois
  pour les flottants, 69 fois pour les entiers (chaque produit crée un entier de
  128 bits, puis `& MASK` un nouvel objet), 78 fois pour la table (plusieurs opérations
  sur des objets par élément). Prédiction 4 confirmée pour `hash_chain` (131 ns ; $R$ de
  69) ; **réfutée** pour `dot` (44,9 ns, sous la borne de 50) et pour `count` (270 ns,
  sous la borne de 400) : l'interpréteur est plus rapide que prévu.

### 10.2 Écritures idiomatiques : aucun gain en compilé, des gains en Python

| $t_{\text{idiom}}/t_{\text{control}}$ (IC 95 %) | `rust` | `go` | `python` |
|---|---:|---:|---:|
| `hash_chain` | 1,017 [0,978 ; 1,027] | 0,987 [0,972 ; 1,007] | 0,884 [0,881 ; 0,887] |
| `dot` | 0,986 [0,970 ; 1,009] | 0,990 [0,972 ; 1,048] | 0,271 [0,268 ; 0,275] |
| `count` | 4,68 [4,64 ; 4,70] | 5,56 [5,48 ; 5,65] | 0,387 [0,383 ; 0,400] |

- **En Rust et en Go, itérateur et boucle indexée donnent le même coût** (0,99 à 1,02),
  comme l'assembleur le laissait prévoir. Prédiction 5 confirmée.
- **En Python, l'écriture idiomatique déplace le travail vers du code natif** :
  `for x in u` coûte 0,88 fois la boucle indexée (prédiction 6 confirmée) ;
  `math.sumprod`, écrit en C, coûte 12,2 ns par élément, 3,7 fois moins que la boucle
  (prédiction 6 confirmée) ; `collections.Counter`, dont la boucle est aussi en C, coûte
  104 ns, 2,6 fois moins que la table écrite en Python, mais **au-dessus** de la borne
  prévue de 80 ns (prédiction 7 réfutée pour Python).
- **Les tables de hachage idiomatiques de Rust et de Go coûtent 4,7 et 5,6 fois la table
  contrôlée** : 16,8 et 19,9 ns par élément (prédiction 7 confirmée pour ces deux
  langages). Ce n'est pas un écart de langage mais d'algorithme : fonction de hachage
  résistante aux attaques (SipHash en Rust), structure générale, agrandissement
  progressif pendant la mesure, contre une table dimensionnée d'avance pour des clés de
  16 bits.
- **Aucune collecte automatique** du ramasse-miettes pendant un échantillon, ni en Go
  ni en Python, y compris pour les `map` et `Counter` créés dans la fenêtre. Prédiction
  10 confirmée.

### 10.3 Bibliothèque native : NumPy bat la boucle C, mais pas au même jeu

| Charge | NumPy, $\tilde t$ | Rapport à `c-O2` | Rapport à la boucle Python contrôlée |
|---|---:|---:|---:|
| `dot` (`np.dot`) | 0,99 ns | 0,659 [0,631 ; 0,766] | 0,022 |
| `count` (`np.bincount`) | 2,79 ns | 0,807 [0,772 ; 0,834] | 0,010 |

- **Un appel NumPy est 45 à 100 fois plus rapide que la boucle Python** qui fait le même
  travail, et plus rapide que la boucle C contrôlée. Ce résultat ne dit rien de Python
  comme langage : le travail est fait par OpenBLAS et par une boucle C de NumPy.
- **Ce n'est pas non plus le même travail que la boucle C.** `np.dot` n'additionne pas
  dans l'ordre (son résultat diffère dans les derniers bits, section 6), ce qui lui
  permet de vectoriser la somme ; `np.bincount` compte par indexation directe d'un
  tableau de 65 536 cases, sans aucune fonction de hachage, ce qui n'est possible que
  parce que les clés sont des entiers denses et petits.
- Prédiction 8 **réfutée** pour `np.dot` (0,99 ns au lieu de 0,15 à 0,6 ns, et 1,5 fois
  plus rapide que C au lieu de 2 à 8 fois) ; confirmée pour `np.bincount` (2,79 ns).

### 10.4 Contrôles, échauffement et mémoire

| Contrôle, étendue par processus | `c-O2` | `c-O3` | `rust` | `go` | `python` |
|---|---|---|---|---|---|
| $T_{\text{bis}}/T$, `hash_chain` | 0,916 à 1,113 | 0,971 à 1,055 | 0,962 à 1,037 | 0,928 à 1,059 | 0,987 à 1,011 |
| $T_{\text{double}}/T$, `hash_chain` | 1,786 à 2,125 | 1,959 à 2,171 | 1,943 à 2,081 | 1,861 à 2,166 | 1,981 à 2,019 |
| $T_{\text{bis}}/T$, `count` idiomatique | | | 0,970 à 1,017 | 0,997 à 1,016 | 0,967 à 1,042 |

- **Prédiction 9 réfutée pour les versions compilées** : l'A/A de `hash_chain` sort de
  l'intervalle 0,97 à 1,03 dans certains processus C, Rust et Go (jusqu'à 0,916 et
  1,113 en `c-O2`), et le contrôle positif de `c-O2` descend à 1,786. Leurs médianes
  restent justes (A/A de 0,983 à 1,015, positif de 1,992 à 2,014). Un échantillon de
  `hash_chain` compilé dure 2 ms, contre 130 ms en Python, dont l'A/A reste entre 0,987
  et 1,011 : une perturbation de la machine pèse davantage sur un échantillon court,
  dans une campagne commencée à une charge moyenne de 3,54. Les écarts entre versions
  de moins de 5 % ne sont donc pas interprétés.
- **Échauffement** : $\rho_0$ médian entre 0,93 et 1,07 pour toutes les versions et
  toutes les mesures ; prédiction 11 confirmée en médiane. Des premiers tours isolés
  atteignent 1,51 (`Counter`) et 1,40 (`dot` en C). En Python, $\rho_0$ dépasse 1 dans
  tous les processus pour `hash_chain` (médianes de 1,04 à 1,06, minimum 1,007) : la spécialisation de
  l'interpréteur coûte quelques pour cent au premier passage, rien de plus.
- **Mémoire** : un processus de mesure occupe 67 Mio en C, 99 à 102 Mio en Go et en Rust
  (qui gardent en plus le fichier lu), et **585 Mio en Python**, 8,7 fois C : chaque
  entier ou flottant d'une liste Python est un objet alloué.

### 10.5 Démarrage : séparé du régime établi

| Commande | $D$ médian (IC 95 %) | 10ᵉ à 90ᵉ centile |
|---|---:|---:|
| `c-O2 --noop` | 0,73 ms [0,66 ; 0,78] | 0,56 à 0,90 ms |
| `c-O3 --noop` | 0,63 ms [0,60 ; 0,74] | 0,54 à 0,86 ms |
| `rust --noop` | 0,87 ms [0,85 ; 0,99] | 0,75 à 1,13 ms |
| `go --noop` | 1,47 ms [1,40 ; 1,55] | 1,20 à 1,64 ms |
| `python --noop` | 19,8 ms [19,7 ; 19,9] | 19,2 à 20,4 ms |
| `python --noop-numpy` | 99,7 ms [99,1 ; 100,1] | 96,9 à 101,2 ms |

- Prédiction 12 confirmée pour les six commandes.
- **Lancer l'interpréteur Python coûte 27 fois un programme C, et importer NumPy ajoute
  environ 80 ms.** Ces durées sont hors des mesures de régime établi ci-dessus : un
  benchmark qui chronométrerait `python script.py` de bout en bout mesurerait d'abord
  le démarrage.

### 10.6 Ce que E1 permet et ne permet pas de conclure

Permet de conclure, sur cette machine et pour ces trois charges :

- à algorithme, données et types identiques, C, Rust et Go ont le même coût à 4 % près ;
  vérifications de bornes et itérateurs n'y changent rien de mesurable ;
- CPython interprète le même algorithme 30 à 78 fois plus lentement que C, selon le type
  d'opérations ;
- les écritures idiomatiques mesurent autant l'algorithme et la bibliothèque que le
  langage : tables de hachage générales 5 fois plus lentes qu'une table dédiée, fonctions
  natives de Python 2,6 à 3,7 fois plus rapides que la boucle Python ;
- NumPy est plus rapide que la boucle C stricte parce qu'il fait un travail différent
  (ordre des additions, indexation directe), pas parce que Python serait rapide ;
- démarrer un interpréteur Python coûte 20 ms, 100 ms avec NumPy.

Ne permet pas de conclure :

- un classement général des langages : trois petites charges, une version de chaque
  chaîne, un processeur ;
- l'effet d'un JIT (celui de CPython était désactivé), de PyPy, de `-march=native` ou de
  l'optimisation à l'édition de liens ;
- le comportement du ramasse-miettes sous une vraie pression d'allocation : aucune
  collecte n'a eu lieu.

**Pour les 13 ms :** le seul démarrage d'un interpréteur Python (19,8 ms) dépasse déjà
13 ms. Si la requête a été mesurée en lançant un client Python neuf (un script, ou un
outil écrit en Python), **la mesure peut être dominée par le démarrage** avant tout
réseau : hypothèse prioritaire pour J2, à tester en séparant le lancement du client de
la requête elle-même.

## 11. Limites et expériences suivantes

- Un CPU (11), une campagne de 8 min commencée à une charge moyenne de 3,54 ; contrôles
  A/A des versions compilées moins bons que les médianes ne le laissent croire.
- Trois charges choisies pour être traduisibles à l'identique ; elles ne représentent
  pas un programme réel.
- Options de compilation « par défaut » de chaque langage (`-O2`/`-O3`,
  `opt-level=3`, `go build`) : d'autres réglages donneraient d'autres résultats.
- Le démarrage est mesuré pour des programmes qui ne font rien ; le coût du chargement
  des bibliothèques utilisées réellement par un programme n'est pas séparé.

Expériences suivantes :

1. **E2, environnements d'exécution** : démarrage détaillé (chargement dynamique,
   initialisation, import), JIT de CPython activé, ramasse-miettes de Go sous pression
   d'allocation.
2. Séparer, pour `hash_chain` en C, l'effet de la taille des données (512 Kio contre
   8 Mio) de celui de la charge de la machine, pour expliquer l'écart avec B2.
3. Mesurer `c-O3` sur `dot` avec plusieurs tailles pour localiser son surcoût.

## 12. Compréhension et prolongement

Questions :

1. Pourquoi C, Rust et Go coûtent-ils la même chose sur `hash_chain` et `dot`, alors que
   leurs compilateurs et leurs règles (vérification de bornes) diffèrent ?
2. Pourquoi l'écart entre Python et C est-il de 30 pour `dot` mais de 69 pour
   `hash_chain` ?
3. `np.dot` est plus rapide que la boucle C. Qu'est-ce qui rend cette comparaison
   injuste, et comment l'écrire pour qu'elle soit contrôlée ?
4. Pourquoi la `HashMap` de Rust coûte-t-elle 5 fois la table contrôlée, et dans quels
   cas ce surcoût est-il justifié ?
5. Un collègue mesure `time python script.py` et conclut que son calcul prend 120 ms.
   Que mesure-t-il réellement ?

Prolongement : écrire une version NumPy **contrôlée** de `dot`, qui additionne dans
l'ordre (par exemple `np.add.accumulate` sur les produits, ou une boucle par blocs).
Prédire son coût avant de mesurer, vérifier que son résultat est exactement celui de la
boucle C, puis comparer à `np.dot`.
