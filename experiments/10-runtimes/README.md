# E2 - Environnements d'exécution : démarrage, échauffement du JIT et ramasse-miettes

## 1. Question et prérequis

**Question :** que se passe-t-il avant et autour du calcul lui-même ? Combien coûte le
démarrage d'un programme selon son environnement d'exécution, et où part ce temps ?
Combien de temps un compilateur à la volée met-il à atteindre son régime établi ? Et que
coûtent, en débit et en pauses, les ramasse-miettes face à une allocation continue ?

Prérequis : [E1](../09-languages/README.md) (même travail dans plusieurs langages,
démarrage de 0,6 ms en C à 100 ms pour Python avec NumPy),
[D1](../07-syscalls/README.md) (coût d'entrée dans le noyau) et
[A2](../02-microbenchmark/README.md) (échauffement et premier passage à froid).

## 2. Notions nécessaires

**Intuition.** Un programme compilé d'avance est un plat préparé : il suffit de le
servir. Un environnement à JIT est un cuisinier qui commence par suivre la recette
lentement, remarque les gestes répétés, puis s'organise pour les faire vite : les
premières assiettes sortent lentement. Un ramasse-miettes est un plongeur qui passe
régulièrement : le service ne s'arrête pas, mais il est parfois gêné.

- **Démarrage** (*startup*) : du lancement du processus au début du travail utile :
  chargement de l'exécutable et des bibliothèques partagées, initialisation de
  l'environnement d'exécution, import des modules.
- **Liaison dynamique** (*dynamic linking*) : les bibliothèques partagées (la
  bibliothèque C) sont chargées et reliées au lancement ; un exécutable **statique** les
  contient déjà.
- **Interpréteur, JIT** (*interpreter*, *just-in-time compiler*) : l'interpréteur exécute
  le code intermédiaire instruction par instruction ; le JIT compile en code machine les
  parties souvent exécutées, pendant l'exécution, souvent par **niveaux** (*tiers*) de
  plus en plus optimisés, et parfois pendant qu'une boucle tourne (*on-stack
  replacement*, OSR).
- **HotSpot** (JVM d'OpenJDK) : interpréteur, puis compilateurs C1 (rapide) et C2
  (optimisant). `-Xint` n'utilise que l'interpréteur. **CDS** (*class data sharing*) :
  classes de la bibliothèque standard préchargées dans une archive ; `-Xshare:off` la
  désactive.
- **V8** (moteur JavaScript de Node) : interpréteur Ignition, puis compilateurs
  successifs jusqu'à TurboFan. `--jitless` n'utilise que l'interpréteur.
- **JIT de CPython** : compilateur expérimental par assemblage de gabarits
  (*copy-and-patch*), activé par la variable `PYTHON_JIT=1`.
- **Ramasse-miettes générationnel** (*generational garbage collector*) : la plupart des
  objets meurent jeunes ; une petite zone jeune est collectée souvent, les survivants
  sont promus dans une zone ancienne, collectée plus rarement. **Pause** (*pause*) :
  période où le programme est arrêté pour la collecte.
- **Go** : collecteur concurrent, non générationnel ; `GOGC` fixe la croissance du tas
  autorisée entre deux collectes (100 : le tas peut doubler).
- **Java** : G1 (par défaut, régions et objectif de pause) ou Serial (un seul fil,
  arrêt complet). **CPython** : comptage de références, plus un collecteur des cycles
  déclenché par le nombre d'objets alloués, désactivable par `gc.disable()`.

### Notations

**Partie 1, démarrage.** Commandes qui se terminent aussitôt, lancées par `posix_spawn`
et attendues par `wait4` :

| Commande (nom dans les données) | Ce qui est lancé |
|---|---|
| `c-dynamic`, `c-static` | programme C vide, lié dynamiquement ou statiquement |
| `rust`, `go` | programme vide en Rust (liaison dynamique à la bibliothèque C) et en Go (statique) |
| `python` | `python3` sur un fichier vide |
| `python-no-site` | `python3 -S` : sans le module `site` (chemins, paquets installés) |
| `python-isolated` | `python3 -I -S` : de plus, sans variables d'environnement ni répertoire utilisateur |
| `python-numpy` | `python3` sur un fichier qui importe NumPy |
| `node`, `node-jitless` | `node` sur un module vide, avec ou sans JIT |
| `java`, `java-no-cds` | JVM sur une classe vide, avec ou sans archive CDS |

**Partie 2, échauffement.** Dans un processus neuf, 300 **pas** consécutifs ; chaque pas
exécute la chaîne de hachage puis le produit scalaire strict de E1 sur $n = 2^{16}$
éléments, chronométrés chacun :

| Mode | Environnement | CPU autorisés |
|---|---|---|
| `c` | C, GCC `-O2` (référence compilée d'avance) | 11 |
| `java`, `java-xint`, `java-2cpu` | HotSpot 17 : JIT, interpréteur seul, JIT sur deux cœurs | 11 ; 11 ; 9 et 11 |
| `node`, `node-jitless`, `node-2cpu` | Node 26 (V8) : JIT, interpréteur seul, JIT sur deux cœurs | 11 ; 11 ; 9 et 11 |
| `python`, `python-jit` | CPython 3.14.4 : sans et avec JIT | 11 |

En JavaScript, la chaîne de hachage s'écrit avec `BigInt` (entiers de taille
arbitraire, réduits par `BigInt.asUintN(64, ...)`) : différence inévitable, comme le
`& MASK` de Python. Les CPU 9 et 11 sont deux cœurs P physiques distincts ; avec un seul
CPU, les fils de compilation du JIT et du ramasse-miettes partagent le cœur du programme.

**Partie 3, allocation.** Un anneau de $L = 2^{20}$ objets de trois entiers de 64 bits ;
chaque **opération** crée un objet et remplace le plus ancien, qui devient inutile.
Après le remplissage, $2^{10}$ **lots** de $B = 2^{13}$ opérations sont chronométrés un
par un (environ 8,4 millions d'opérations) :

| Mode | Gestion de la mémoire |
|---|---|
| `c` | `malloc` et `free` explicites (glibc) |
| `go-gogc100`, `go-gogc400` | Go 1.26, `GOGC=100` (par défaut) ou `GOGC=400` |
| `java-g1`, `java-serial` | HotSpot 17, collecteur G1 ou Serial |
| `node` | V8, réglages par défaut |
| `python-gc`, `python-nogc` | CPython, collecteur des cycles actif ou désactivé |

**Symboles :**

| Symbole | Signification | Unité |
|---|---|---|
| $D$ | durée de démarrage d'une commande | ms |
| $T_k$ | durée du pas $k$ d'une charge ($k = 0, \ldots, 299$) | ms |
| $T_\infty$ | régime établi d'un processus : médiane de $T_{200}, \ldots, T_{299}$ | ms |
| $\rho_0 = T_0 / T_\infty$ | rapport du premier pas au régime établi | |
| $E = \sum_k \max(0,\ T_k - T_\infty)$ | **surcoût d'échauffement** : temps perdu par rapport au régime établi | ms |
| $R = T_\infty / T_\infty^{\text{c}}$ | rapport du régime établi à celui de C (médianes entre processus) | |
| $c$ | coût par opération d'allocation : durée totale des lots divisée par le nombre d'opérations | ns |
| $b_{50}$, $b_{99}$, $b_{\max}$ | médiane, 99ᵉ centile et maximum des durées de lot d'un processus | ms |
| $N_{\text{gc}}$, $P_{\text{gc}}$ | nombre de collectes et durée totale rapportée par l'environnement pendant les lots | sans unité ; ms |

Ce qui est **garanti** : les résultats des calculs et l'état final de l'anneau
(vérifiés), les options de chaque processus. Ce qui **dépend de l'environnement
d'exécution et de sa version** : seuils et niveaux du JIT, dimensionnement des zones du
ramasse-miettes, travail fait au démarrage. Ce qui **dépend de la machine** : tout le
reste. $N_{\text{gc}}$ et $P_{\text{gc}}$ sont ce que chaque environnement déclare, avec
ses propres définitions (pauses seules pour Go, temps de collecte pour Java, durées des
événements pour V8, durées des collectes pour CPython) : ils ne se comparent pas d'un
environnement à l'autre.

## 3. Modèles et prédictions, écrits avant la campagne

### 3.1 Transparence

Avant d'écrire ce qui suit, j'avais vu :

- les résultats d'E1 : démarrage médian de 0,73 ms (C), 0,87 ms (Rust), 1,47 ms (Go),
  19,8 ms (Python), 99,7 ms (Python avec NumPy) ; régime établi de la chaîne de hachage
  et du produit scalaire (1,90 et 1,50 ns par élément en C, 131 et 44,9 ns en Python) ;
- en vérifiant les outils de décomposition, une ligne de `python3 -X importtime` (import
  du module `site` : 7,7 ms cumulées) et une de `GODEBUG=inittrace=1` (initialisation
  de `os` à 1,1 ms du démarrage du programme Go) ;
- un essai de dimensionnement (10 pas, ou l'allocation complète) dont seule la durée
  totale de quelques processus a été lue (0,10 à 0,22 s pour 10 pas ; 0,74 à 2,1 s pour
  l'allocation complète en Java Serial, Node et Python).

### 3.2 Modèles

**Échauffement.** Un pas coûte $T_k = T_\infty + e_k$, où $e_k \geq 0$ est le surcoût
d'une exécution non encore optimisée (interprétation, puis code de premier niveau), plus
le temps que les fils du JIT prennent au programme quand ils partagent son cœur. Le
surcoût total est

$$
E = \sum_{k} \max(0,\ T_k - T_\infty).
$$

Sur deux cœurs, la compilation se fait en parallèle : $E$ doit baisser, pas $T_\infty$.

**Allocation.** Une opération coûte l'allocation, l'écriture de l'objet et, en
moyenne, la part de collecte qu'elle provoque :

$$
c \approx c_{\text{alloc}} + \frac{P_{\text{gc}} + W_{\text{gc}}}{N_{\text{op}}},
$$

où $W_{\text{gc}}$ est le travail du ramasse-miettes fait en dehors des pauses et
$N_{\text{op}}$ le nombre d'opérations. Les pauses n'augmentent que quelques lots :
elles se voient dans $b_{99}$ et $b_{\max}$, pas dans $b_{50}$.

### 3.3 Prédictions

Démarrage (médianes) :

1. `c-static` coûte 0,3 à 0,7 fois `c-dynamic`.
2. `python-no-site` coûte 0,5 à 0,8 fois `python` ; `python-isolated` au plus autant que
   `python-no-site`.
3. `node` : 20 à 60 ms ; `node-jitless` entre 0,8 et 1,2 fois `node`.
4. `java` : 30 à 80 ms ; `java-no-cds` entre 1,3 et 3 fois `java`.

Échauffement :

5. `c` : $\rho_0 \leq 1{,}5$ et $E$ inférieur à 5 pas de régime établi.
6. `java` : $R$ entre 0,9 et 1,5 pour les deux charges ; $\rho_0 \geq 5$ pour la chaîne de
   hachage. `java-xint` : $R$ entre 20 et 100.
7. `node` : produit scalaire, $R$ entre 1,0 et 2,0 ; chaîne de hachage en `BigInt`, $R$
   entre 1 et 20 (confiance faible : tout dépend de la capacité de V8 à ramener `BigInt`
   à des entiers machine). `node-jitless` : produit scalaire, $R$ entre 30 et 150.
8. Deux cœurs : $E$ de `java-2cpu` et de `node-2cpu` au plus 0,67 fois celui du même
   environnement sur un cœur ; $T_\infty$ inchangé à 10 % près.
9. `python-jit` : $T_\infty$ entre 0,85 et 1,1 fois `python`, pour les deux charges ;
   $\rho_0 \leq 1{,}3$ dans les deux modes.

Allocation :

10. `c` : $c$ entre 10 et 40 ns ; $b_{\max} \leq 3\,b_{50}$.
11. `go-gogc100` : $c$ entre 20 et 60 ns, $N_{\text{gc}}$ entre 3 et 30 ; `go-gogc400` :
    au plus un tiers de ces collectes, $c$ entre 0,7 et 1,0 fois `go-gogc100`, mémoire
    maximale plus élevée.
12. `java-g1` et `java-serial` : $c$ entre 5 et 30 ns ; $b_{\max} \geq 10\,b_{50}$ (pauses
    de collecte), et plus encore pour Serial que pour G1.
13. `node` : $c$ entre 20 et 80 ns ; $b_{\max} \geq 10\,b_{50}$.
14. `python-gc` : $c$ entre 150 et 400 ns ; `python-nogc` entre 0,7 et 0,95 fois
    `python-gc` ; $b_{\max} \geq 3\,b_{50}$ pour `python-gc`.

## 4. Code et parties importantes

- Échauffement : [`src/c/warm.c`](src/c/warm.c), [`src/java/Warm.java`](src/java/Warm.java),
  [`src/node/warm.mjs`](src/node/warm.mjs), [`src/python/warm.py`](src/python/warm.py) :
  mêmes boucles que E1, lecture du même type de fichier d'entrée (généré par `warm.c`),
  chronométrage de chaque pas par l'horloge monotone de l'environnement (`clock_gettime`,
  `System.nanoTime`, `process.hrtime.bigint`, `time.perf_counter_ns`).
- Allocation : [`src/c/churn.c`](src/c/churn.c), [`src/go/churn.go`](src/go/churn.go),
  [`src/java/Churn.java`](src/java/Churn.java), [`src/node/churn.mjs`](src/node/churn.mjs),
  [`src/python/churn.py`](src/python/churn.py) : même anneau, même objet ; collectes
  relevées par `runtime.ReadMemStats` (Go), `GarbageCollectorMXBean` (Java),
  `PerformanceObserver` (V8) et `gc.callbacks` (CPython).
- Démarrage : programmes vides dans `src/*/noop.*` ; [`src/c/launch.c`](src/c/launch.c),
  repris d'E1.
- Chaque programme écrit dans ses métadonnées les CPU qui lui sont autorisés, lus dans
  `/proc/self/status`.
- [`prepare.py`](prepare.py), [`run.sh`](run.sh) : plan mélangé et lancement de chaque
  mode avec ses options ; [`verify.py`](verify.py) ; [`analyze.py`](analyze.py).

## 5. Commandes

```sh
make check      # correction : tailles réduites, résultats recalculés en Python
make quick      # validation de la chaîne
make campaign   # campagne documentée ; refuse d'écraser data/campaign
make analyze    # résumés et figures depuis data/campaign
```

Les binaires Java sont compilés par `javac --release 17` et exécutés par Java 17 ; Node
et CPython sont ceux du système.

## 6. Vérification de correction, indépendante de la mesure

- Échauffement : chaque résultat (chaîne de hachage exacte, produit scalaire au bit
  près) est comparé à celui recalculé en Python à partir du fichier d'entrée, dont
  l'empreinte SHA-256 est contrôlée ; l'état du JIT déclaré par chaque processus doit
  correspondre à son mode.
- Allocation : le nombre d'opérations et la somme de contrôle de l'anneau final
  ($\sum (k_i + a_i + b_i)$ sur les $L$ derniers objets) sont recalculés.
- Tous les processus : les CPU autorisés qu'ils déclarent doivent être ceux du plan.
- Démarrage : code de sortie 0 pour chaque lancement ; traces de décomposition présentes.
- Des essais de mutation (liste de CPU modifiée) font bien échouer la vérification.

## 7. Protocole de la campagne

- Parties 2 et 3 : 9 modes d'échauffement et 8 modes d'allocation, 10 processus
  indépendants chacun, soit 170 processus dans un ordre aléatoire fixé (graine
  `20260923`).
- Unité statistique : le processus. Par processus : $T_\infty$, $\rho_0$, $E$ par charge ;
  $c$, $b_{50}$, $b_{99}$, $b_{\max}$, $N_{\text{gc}}$, $P_{\text{gc}}$ et mémoire maximale.
  Entre processus : médiane et IC 95 % bootstrap percentile (10 000 tirages) ; rapports
  entre modes : rapports des médianes de groupes indépendants, IC par bootstrap de
  chaque groupe.
- Partie 1 : 50 répétitions de chaque commande, dans un ordre tiré au hasard à chaque
  répétition, depuis le CPU 11 ; puis 20 répétitions des traces de décomposition
  (`-X importtime` pour Python avec et sans NumPy, `GODEBUG=inittrace=1` pour Go,
  `-Xlog:startuptime` pour Java).
- Aucun réglage global : toutes les options sont propres à chaque processus.

## 8. Données brutes

- [`data/campaign/`](data/campaign/) : `plan.csv` (écrit avant la mesure) ; pour chaque
  processus d'échauffement, `warm-NNN.csv` (une ligne par pas et par charge : durée,
  résultat) et `warm-NNN-meta.csv` (environnement, état du JIT, CPU autorisés) ; pour
  chaque processus d'allocation, `churn-NNN.csv` (durée de chaque lot) et
  `churn-NNN-meta.csv` (durée totale, somme de contrôle, collectes, mémoire maximale,
  CPU autorisés) ; `startup.csv` (chaque démarrage) ; `decomposition/` (traces brutes
  de `-X importtime`, `GODEBUG=inittrace=1` et `-Xlog:startuptime`) ;
  `input.sha256`.
- [`data/environment-campaign.txt`](data/environment-campaign.txt) : machine, versions
  de GCC, Rust, Go, Java, Node et CPython, options, empreintes SHA-256.
- Résumés : `reports/campaign-startup.csv`, `-startup-ratios.csv`, `-decomposition.csv`,
  `-warmup.csv` ($T_\infty$, $R$, $\rho_0$, $E$), `-warmup-ratios.csv`, `-gc.csv` ($c$,
  $b_{50}$, $b_{99}$, $b_{\max}$, $N_{\text{gc}}$, $P_{\text{gc}}$, mémoire),
  `-gc-ratios.csv`.

La campagne a duré environ 4 min, avec une charge moyenne de 1,31 au départ. Les 54 000
pas d'échauffement ont un résultat exact, les 170 processus ont une somme de contrôle
exacte et ont tourné sur les CPU prévus, et les 600 démarrages se sont terminés
normalement. Aucune observation retirée.

## 9. Figures

- [`figures/campaign-startup.pdf`](figures/campaign-startup.pdf) : durée de démarrage $D$
  de chaque commande, un point par répétition, médiane et IC 95 %.
- [`figures/campaign-warmup.pdf`](figures/campaign-warmup.pdf) : coût par élément de
  chaque pas depuis le lancement, pour Java (a, b), Node (c, d) et CPython (e, f), chaîne
  de hachage à gauche et produit scalaire à droite ; trait épais : médiane des 10
  processus ; traits fins : chaque processus ; pointillé noir : C.
- [`figures/campaign-gc.pdf`](figures/campaign-gc.pdf) : coût par opération d'allocation,
  un point par processus (a) ; fonction de survie des durées de lot divisées par la
  médiane $b_{50}$ de leur processus, tous processus d'un mode réunis (b). Plus une courbe
  s'étend vers la droite, plus certains lots ont été longs par rapport à un lot ordinaire.

Les axes sont logarithmiques, sauf l'axe horizontal du panneau (a) de la dernière
figure.

## 10. Résultats observés et interprétation

Médianes entre répétitions (démarrage) ou entre 10 processus (échauffement,
allocation).

### 10.1 Démarrage : du chargement des bibliothèques à l'initialisation des modules

| Commande | $D$ médian (IC 95 %) | 10ᵉ à 90ᵉ centile |
|---|---:|---:|
| `c-static` | 0,58 ms [0,56 ; 0,61] | 0,45 à 0,66 ms |
| `c-dynamic` | 0,73 ms [0,69 ; 0,76] | 0,62 à 0,85 ms |
| `rust` | 0,96 ms [0,90 ; 1,02] | 0,81 à 1,10 ms |
| `go` | 1,22 ms [1,19 ; 1,28] | 1,07 à 1,41 ms |
| `python-no-site` | 9,6 ms [9,3 ; 9,8] | 8,7 à 11,2 ms |
| `python-isolated` | 9,6 ms [9,3 ; 9,9] | 8,9 à 11,8 ms |
| `python` | 16,8 ms [16,3 ; 17,2] | 15,5 à 22,0 ms |
| `node-jitless` | 30,4 ms [29,7 ; 31,5] | 27,6 à 35,5 ms |
| `node` | 30,8 ms [30,2 ; 32,5] | 27,8 à 35,8 ms |
| `java` | 58,9 ms [58,0 ; 60,1] | 56,0 à 64,5 ms |
| `java-no-cds` | 75,8 ms [74,7 ; 78,4] | 72,7 à 82,8 ms |
| `python-numpy` | 91,6 ms [90,5 ; 96,1] | 88,6 à 102,3 ms |

- **La liaison dynamique coûte environ 0,15 ms** : `c-static` coûte 0,80 fois
  `c-dynamic`. Prédiction 1 **réfutée** (0,3 à 0,7 prévu) : l'essentiel des 0,7 ms est
  ailleurs (création du processus, `exec`, premiers défauts de page), commun aux deux.
- **Python passe 43 % de son démarrage à importer `site`** : `python -S` coûte 0,57 fois
  `python` (prédiction 2 confirmée). La trace `-X importtime` attribue 6,4 ms à l'import
  de `site`, sur 10,1 ms d'imports au total. `-I` n'ajoute rien de mesurable (rapport
  1,006 [0,966 ; 1,042]).
- **Importer NumPy coûte 64,7 ms** selon la même trace (74,5 ms d'imports au total) :
  `python-numpy` coûte 5,5 fois `python`.
- **Node démarre en 31 ms, avec ou sans JIT** (rapport 0,987) : le JIT ne compile rien
  au démarrage d'un module vide. Prédiction 3 confirmée.
- **La JVM démarre en 59 ms**, dont 48 ms pour créer la machine virtuelle selon
  `-Xlog:startuptime` : 23,5 ms pour initialiser le système de modules, 8,6 ms pour la
  phase « Genesis », 4,6 ms pour les classes de `java.lang`. Sans archive CDS, le
  démarrage prend 17 ms de plus (rapport 1,287) : prédiction 4 confirmée pour la durée,
  **réfutée de peu** pour le rapport (borne basse 1,3).
- Go : la trace `inittrace` place la fin des initialisations de paquets à 0,072 ms du
  démarrage de son environnement d'exécution ; les 1,2 ms mesurées se passent donc
  presque entièrement avant (création du processus, chargement, amorçage du runtime),
  ce que la trace ne décompose pas.

### 10.2 Échauffement : le JIT atteint C en quelques pas, ou jamais

| Mode | Chaîne : $T_\infty$ (ns/élément) | $R$ | $\rho_0$ | Produit : $T_\infty$ (ns/élément) | $R$ | $\rho_0$ |
|---|---:|---:|---:|---:|---:|---:|
| `c` | 1,60 | 1 | 1,09 | 0,805 | 1 | 1,05 |
| `java` | 1,61 | 1,001 | 13,7 | 0,805 | 1,000 | 25,6 |
| `java-2cpu` | 1,61 | 1,001 | 14,0 | 0,806 | 1,002 | 31,9 |
| `java-xint` | 18,2 | 11,4 | 1,00 | 18,1 | 22,5 | 1,00 |
| `node` | 6,58 | 4,10 [3,99 ; 55,7] | 10,0 | 0,919 | 1,14 [1,12 ; 2,27] | 28,3 |
| `node-2cpu` | 6,17 | 3,84 [3,74 ; 55,4] | 10,6 | 0,918 | 1,14 [1,12 ; 2,07] | 12,4 |
| `node-jitless` | 122 | 76,2 | 1,04 | 44,8 | 55,7 | 1,03 |
| `python` | 129 | 80,6 | 1,00 | 43,9 | 54,5 | 1,00 |
| `python-jit` | 120 | 75,0 | 1,01 | 40,4 | 50,2 | 1,03 |

| Surcoût d'échauffement $E$ (médiane, en pas de régime établi) | Chaîne | Produit |
|---|---:|---:|
| `c` | 0,58 ms (5,5) | 0,51 ms (9,6) |
| `java`, `java-2cpu` | 7,6 ms (72) ; 5,8 ms (55) | 10,2 ms (194) ; 9,0 ms (169) |
| `node`, `node-2cpu` | 129 ms (302) ; 138 ms (347) | 6,4 ms (98) ; 3,6 ms (49) |
| `java-xint`, `node-jitless`, `python`, `python-jit` | 4,8 à 7,1 pas | 4,6 à 8,5 pas |

- **HotSpot rejoint exactement C** : $R$ vaut 1,001 et 1,000. Le premier pas coûte 14
  et 26 fois le régime établi, puis le code compilé prend le relais dès le 3ᵉ à 6ᵉ pas
  (figure, a et b). Prédiction 6 confirmée pour $R$ et $\rho_0$ ; l'interpréteur seul
  coûte 11,4 fois C sur la chaîne (**réfuté**, 20 à 100 prévu) et 22,5 fois sur le
  produit (confirmé).
- **V8 rejoint presque C sur les flottants** (1,14 fois) et reste 4,1 fois plus lent sur
  la chaîne en `BigInt`, dans l'intervalle prévu. Prédiction 7 confirmée pour les
  médianes, et pour l'interpréteur seul (55,7 fois).
- **Le code optimisé de V8 arrive tard et n'est pas stable.** Sur la chaîne, tous les
  processus passent 50 à 150 pas (environ 150 ms de calcul) sur un palier à 24 ns par
  élément avant de descendre vers 6 ns (figure, c). Puis **6 processus sur 20** (3 en
  `node`, 3 en `node-2cpu`) rebasculent vers environ 89 ns par élément et y restent ;
  dans ces mêmes processus, le produit scalaire ralentit aussi, vers 1,7 à 2,0 ns au
  lieu de 0,91. L'intervalle de $R$ (3,99 à 55,7) traduit ces deux régimes. Lecture
  exploratoire : un effet qui touche tout le processus, comme une désoptimisation suivie
  d'un code qui alloue des `BigInt` et sollicite le ramasse-miettes pendant le produit
  scalaire, est plausible ; rien ici ne le démontre.
- **$E$ ne mesure pas seulement l'échauffement.** Pour les modes sans JIT, où aucune
  compilation n'a lieu, $E$ vaut déjà 4,6 à 9,6 pas : la somme des écarts positifs au
  régime établi additionne aussi le bruit. Seuls les écarts nettement au-dessus de ce
  plancher sont un échauffement : environ 55 à 200 pas pour HotSpot, 50 à 350 pour V8.
- **Deux cœurs ne réduisent pas nettement l'échauffement.** $E$ de `java-2cpu` vaut 0,76
  et 0,88 fois celui de `java` (intervalles contenant 1) ; celui de `node-2cpu` vaut 1,07
  fois celui de `node` sur la chaîne, et 0,56 [0,38 ; 0,92] sur le produit. Prédiction 8
  **réfutée**, sauf pour le produit scalaire de Node. Le régime établi ne change pas
  (1,000 et 1,002 pour Java).
- **Le JIT de CPython gagne 7 à 8 %** ($T_\infty$ de 0,930 et 0,922 fois `python`), sans
  échauffement visible. Prédiction 9 confirmée.
- **Données et régime établi de C** : la chaîne coûte ici 1,60 ns par élément sur
  $2^{16}$ éléments (512 Kio), contre 1,90 ns en E1 sur 8 Mio et 1,61 ns en B2 sur
  512 Kio. Lecture exploratoire : l'écart d'E1 tient à la taille des données plutôt
  qu'à la charge de la machine.

### 10.3 Ramasse-miettes : débit et pauses ne se règlent pas ensemble

| Mode | $c$ (ns/op) | $b_{50}$ | $b_{99}$ | $b_{\max}$ | $b_{\max}/b_{50}$ | $N_{\text{gc}}$ | $P_{\text{gc}}$ déclaré | Mémoire |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `c` | 9,4 | 0,074 ms | 0,125 ms | 0,18 ms | 2,2 | 0 | | 42 Mio |
| `go-gogc100` | 42,5 | 0,199 ms | 1,68 ms | 8,5 ms | 42 | 6 | 0,14 ms | 81 Mio |
| `go-gogc400` | 31,2 | 0,236 ms | 0,79 ms | 8,4 ms | 36 | 1 | 0,02 ms | 147 Mio |
| `java-g1` | 62,4 | 0,142 ms | 2,61 ms | 61 ms | 444 | 7 | 318 ms | 414 Mio |
| `java-serial` | 49,9 | 0,046 ms | 0,49 ms | 146 ms | 3 269 | 6 | 350 ms | 288 Mio |
| `node` | 130 | 0,163 ms | 43,0 ms | 51 ms | 313 | 26 | 921 ms | 616 Mio |
| `python-gc` | 187 | 1,49 ms | 2,41 ms | 2,9 ms | 1,9 | 0 | 0 | 184 Mio |
| `python-nogc` | 187 | 1,49 ms | 2,40 ms | 2,9 ms | 2,0 | 0 | 0 | 184 Mio |

- **C** : 9,4 ns par opération, lots réguliers ($b_{\max} = 2{,}2\ b_{50}$). Prédiction 10
  **réfutée de peu** pour $c$ (borne basse 10 ns), confirmée pour la régularité.
- **Go** : 6 collectes en `GOGC=100` pour 0,14 ms de pauses déclarées, mais des lots
  jusqu'à 8,5 ms. Avec un seul CPU, le marquage concurrent prend le processeur au
  programme : c'est un ralentissement, pas une pause au sens de Go, et il ne dépend pas
  de `GOGC` ($b_{\max}$ de 0,98 fois), car marquer coûte en proportion des objets vivants.
  `GOGC=400` fait 1 collecte au lieu de 6, abaisse $c$ à 0,735 fois et demande 1,8 fois
  plus de mémoire. Prédiction 11 confirmée.
- **Java** : allouer est très rapide ($b_{50}$ de Serial = 5,6 ns par opération), mais
  les objets vivent un million d'opérations : ils survivent aux collectes jeunes et
  sont recopiés. Le coût moyen monte à 50 à 62 ns, et une collecte arrête le programme
  jusqu'à 146 ms (Serial) ou 61 ms (G1). G1 raccourcit la pire pause d'un facteur 2,4
  mais coûte 1,25 fois plus par opération et 1,4 fois plus de mémoire. Prédiction 12
  **réfutée** pour $c$ (5 à 30 ns prévus), confirmée pour les pauses et leur ordre.
- **Node** : 26 collectes déclarées pour 921 ms, soit la plus grande partie du temps de
  mesure ; 1 % des lots dépasse 43 ms. Prédiction 13 **réfutée** pour $c$ (130 ns au lieu
  de 20 à 80), confirmée pour les pauses.
- **CPython : aucune collecte, avec ou sans `gc`.** Le collecteur des cycles se déclenche
  quand les allocations d'objets suivis dépassent les libérations d'un seuil ; ici,
  chaque opération alloue un objet et en libère un, par comptage de références, et le
  compteur ne monte pas. Les deux modes sont identiques (rapport 1,000). Prédiction 14
  confirmée pour $c$ (187 ns), **réfutée** pour l'effet de `gc.disable()` et pour les
  pauses.

### 10.4 Ce que E2 permet et ne permet pas de conclure

Permet de conclure, sur cette machine :

- démarrer un programme coûte moins de 1,3 ms compilé d'avance, 17 ms pour CPython (dont
  6,4 ms pour `site`), 31 ms pour Node, 59 ms pour la JVM, 92 ms pour Python avec NumPy ;
- un JIT peut rejoindre exactement C (HotSpot) ou s'en approcher (V8 sur les flottants),
  après un premier passage 10 à 28 fois plus lent ; son régime établi peut aussi changer
  en cours de route (6 processus Node sur 20) ;
- le coût d'allocation moyen d'un environnement à ramasse-miettes dépend de la durée de
  vie des objets bien plus que de l'allocation elle-même, et ses pires lots vont de
  8,5 ms (Go) à 146 ms (Java Serial) pour 1 million d'objets vivants ;
- les compteurs de collectes ne se comparent pas entre environnements : Go déclare
  0,14 ms de pauses pour des lots ralentis de 8,5 ms.

Ne permet pas de conclure :

- ce que coûterait un vrai service : taille des tas, durées de vie et réglages par
  défaut changent tout ;
- la cause de la rebascule de V8 ;
- l'effet de plusieurs cœurs sur le ramasse-miettes : toute l'allocation était sur un
  seul CPU, ce qui défavorise les collecteurs concurrents ou parallèles.

**Pour les 13 ms :** trois mécanismes de cette expérience atteignent seuls cet ordre de
grandeur dans un environnement neuf ou chargé : démarrer Node (31 ms) ou la JVM (59 ms),
exécuter la première requête dans du code encore interprété (le premier pas Java coûte
14 à 26 fois le régime établi), et subir une collecte pendant la requête (jusqu'à 61 ms
en G1, 51 ms en Node). À vérifier dans J2 : environnement du client et du serveur,
requête mesurée à froid ou après échauffement, collectes relevées pendant la mesure.

## 11. Limites et expériences suivantes

- Une version de chaque environnement, leurs réglages par défaut, un seul CPU pour
  l'allocation ; campagne courte (4 min) à charge moyenne de 1,31.
- $P_{\text{gc}}$ et $N_{\text{gc}}$ ont des définitions propres à chaque environnement.
- $E$ additionne le bruit : un plancher de 5 à 10 pas existe même sans JIT.
- La décomposition du démarrage repose sur les traces de chaque environnement ; Node et
  Rust ne sont pas décomposés.

Expériences suivantes :

1. **F1, processus et threads** : coût de création d'un processus et d'un thread, et
   réutilisation de workers, qui prolongent la mesure du démarrage.
2. Relancer l'allocation Java et Go sur plusieurs CPU pour mesurer ce que la
   concurrence du collecteur change aux pauses.
3. Observer la rebascule de V8 avec `--trace-deopt` et `--trace-gc` dans les processus
   concernés.

## 12. Compréhension et prolongement

Questions :

1. Pourquoi un exécutable statique ne démarre-t-il que 0,15 ms plus vite, et où passe le
   reste des 0,7 ms ?
2. Pourquoi la JVM atteint-elle exactement le régime établi de C, et pourquoi son premier
   pas est-il pourtant 14 fois plus lent ?
3. Que signifie un surcoût d'échauffement de « 5 pas » pour un programme qui n'a pas de
   JIT, et comment corriger la mesure de $E$ pour ne plus compter le bruit ?
4. Go déclare 0,14 ms de pauses mais des lots de 8,5 ms. Lequel de ces deux nombres
   compte pour la latence d'une requête ?
5. Pourquoi `gc.disable()` ne change-t-il rien ici, et quel programme Python en serait
   au contraire fortement affecté ?

Prolongement : modifier la charge d'allocation pour que les objets meurent jeunes
(anneau de $2^{10}$ objets au lieu de $2^{20}$). Prédire, avant de mesurer, l'effet sur $c$
et $b_{\max}$ en Java et en Go, puis comparer.
