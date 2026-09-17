# C1 - Parcours mémoire : localité, lignes de cache, bande passante

## 1. Question et prérequis

**Question :** lire un élément de 8 octets coûte-t-il toujours la même chose ?
Comment le coût d'un accès et le débit de lecture évoluent-ils avec la taille des
données et l'ordre des accès, et comment éviter d'attribuer une transition à un
cache sur la seule forme d'une courbe ?

Prérequis : [B1](../03-compilation/README.md), qui a observé une convergence des
débits au-delà de 2 Mio sans pouvoir l'expliquer, et
[B2](../04-dependencies-branches/README.md) (chaînes de dépendance, exécution dans le
désordre). Le protocole de mesure est celui d'A2 à B2.

## 2. Notions nécessaires

**Intuition.** La mémoire est une bibliothèque à plusieurs étages. Le bureau (cache
L1) contient peu de livres mais à portée de main ; la réserve (mémoire vive) en
contient beaucoup, mais chaque trajet est long. Un lecteur qui lit les livres dans
l'ordre des rayonnages peut en faire monter plusieurs d'avance ; un lecteur qui les
demande au hasard attend à chaque fois.

- **Hiérarchie mémoire** (*memory hierarchy*) : registres, caches L1, L2, L3, mémoire
  vive (DRAM). Plus un niveau est grand, plus un accès y est lent.
- **Cache** (*CPU cache*) : copie, proche du processeur, d'une partie de la mémoire.
  **Défaut de cache** (*cache miss*) : donnée absente, cherchée au niveau suivant.
- **Ligne de cache** (*cache line*) : unité de copie entre niveaux, ici 64 octets.
  Lire un octet charge toute sa ligne.
- **Localité** (*locality*) : spatiale (accès proches les uns des autres) ou
  temporelle (mêmes données réutilisées).
- **Préchargement matériel** (*hardware prefetching*) : le processeur détecte un motif
  d'accès et charge d'avance les lignes suivantes. Il ne peut pas être désactivé
  sans droits d'administration.
- **Page** (*page*) et **TLB** (*translation lookaside buffer*) : la mémoire virtuelle
  est découpée en pages de 4 Kio ; la TLB est un petit cache des traductions
  d'adresses. Au-delà de sa couverture, un accès lointain peut aussi coûter une
  traduction. Étudié en C2 ; ici, présent mais non séparé.
- **Bande passante** (*memory bandwidth*) : octets lus par seconde quand l'ordre des
  accès est prévisible. **Latence d'accès** (*access latency*) : temps pour obtenir
  une donnée précise. Un parcours séquentiel mesure surtout la première, un parcours
  aléatoire devrait mesurer la seconde.
- **Demi-octave** : facteur $\sqrt{2}$ entre deux tailles successives ; les tailles
  vont par paires 4 ; 6 ; 8 ; 12 ; 16 Kio...

### Notations

**Données.** Un tableau de $N$ entiers de 8 octets, rempli par le générateur
SplitMix64, aligné sur une page, de taille $S = 8N$ octets. $S$ va de 4 Kio à
256 Mio par demi-octaves (33 tailles).

**Mesures.** Chaque échantillon fait $2^{20}$ accès ; l'accès de rang $j$ lit
l'élément d'indice $i_j$. Le départ $i_0$ et un **sel** $\sigma$ (nombre aléatoire qui
rend la suite d'indices différente à chaque échantillon) sont tirés au hasard.

| Mesure (nom dans les données) | Indice lu à l'accès $j$ | Rôle |
|---|---|---|
| `stride_1` | $i_j = i_{j-1} + 1$ (modulo $N$) | parcours séquentiel |
| `stride_1_bis` | idem | contrôle A/A : rapport vrai 1 |
| `stride_1_double` | idem, $2^{21}$ accès | contrôle positif : durée attendue × 2 |
| `stride_17` | $i_j = i_{j-1} + 17$ (136 octets plus loin) | une nouvelle ligne à chaque accès, même page environ 30 fois de suite |
| `stride_513` | $i_j = i_{j-1} + 513$ (4 104 octets) | une nouvelle page à chaque accès |
| `stride_4097` | $i_j = i_{j-1} + 4\,097$ (32 776 octets) | 8 pages plus loin à chaque accès |
| `random` | $i_j = \left\lfloor h(\sigma, j) \cdot N / 2^{64} \right\rfloor$, où $h$ mélange les bits de $\sigma$ et $j$ | accès indépendants, sans motif |
| `pair_same_line` | 2 éléments voisins, octets 24 à 39 d'une ligne tirée au hasard | une ligne par accès |
| `pair_split_line` | 2 éléments voisins, octets 56 à 71 d'une ligne tirée au hasard | deux lignes par accès |

Les indices ne dépendent **jamais** des valeurs lues : les accès aléatoires sont
indépendants entre eux et le processeur peut en lancer plusieurs à la fois. Les
accès dépendants sont l'objet de C2.

**Symboles :**

| Symbole | Signification | Unité |
|---|---|---|
| $S$ | taille des données | Kio, Mio |
| $c(S)$ | coût par accès : durée de l'échantillon divisée par le nombre d'accès ; médiane des tours mesurés dans un processus | ns |
| $D$ | débit de lecture : octets lus par seconde, $D = 8/c$ (16/$c$ pour les paires) | Gio/s |
| $\lambda(S_i)$ | pente locale du coût de `random`, centrée sur la taille $S_i$ (définie en section 3) | |
| $G$ | critère d'attribution au L3 : $G = c(16\ \text{Mio}) / c(1\ \text{Mio})$ pour `random` | |
| $c_{\text{split}}/c_{\text{same}}$ | rapport de `pair_split_line` à `pair_same_line`, par processus | |
| $c_{\text{bis}}/c_1$ | contrôle A/A : `stride_1_bis` sur `stride_1` | |
| $T_{\text{double}}/T_1$ | contrôle positif : durée de `stride_1_double` sur durée de `stride_1` | |

**Cœurs.** Les mêmes mesures sont faites sur un cœur P (CPU 11), un cœur E (CPU 19)
et un cœur LP-E (CPU 21). Caches **annoncés par le noyau**
(`/sys/devices/system/cpu/cpu*/cache`), sans être mesurés :

| CPU | Type | L1d | L2 | L3 |
|---|---|---|---|---|
| 11 | P | 48 Kio | 2 Mio (partagé avec le CPU 10) | 24 Mio (CPU 0 à 19) |
| 19 | E | 32 Kio | 2 Mio (partagé par les CPU 16 à 19) | 24 Mio (CPU 0 à 19) |
| 21 | LP-E | 32 Kio | 2 Mio (partagé avec le CPU 20) | **aucun** |

Le cœur LP-E n'a pas de cache L3 : une transition attribuée au L3 doit s'y comporter
différemment. C'est le **contrôle d'attribution**.

Ce qui est **garanti** : les valeurs lues (vérifiées). Ce qui **dépend de la
machine** : latences des niveaux, préchargeurs, mémoire vive. Ce qui **reste
hypothèse** : l'attribution d'une transition à un niveau précis.

## 3. Analyse statique et prédictions, écrites avant la campagne

### 3.1 Ce que montre l'assembleur

- `walk_stride` : l'indice avance par `add`, `cmp`, `cmovae`, une chaîne d'environ
  deux instructions portée par la boucle, indépendante des valeurs lues.
- `walk_random` : l'indice est calculé à partir du seul rang $j$ (xor, décalages, une
  multiplication, un produit de 128 bits `mul`) ; seul le compteur relie les
  itérations.
- `walk_pair` : GCC lit les deux éléments voisins en **une seule lecture de
  16 octets** (`movdqu`), qui recouvre deux lignes dans le cas `pair_split_line`.

### 3.2 Modèles et prédictions

**Transparence :** un essai de mise au point (cœur P, 2 tours) n'a servi qu'à mesurer
la durée totale d'un tour (1,4 s) ; ses résultats par parcours n'ont pas été
examinés.

**Pente locale.** Pour repérer une transition sans choisir une taille à l'œil, on
calcule, pour chaque taille $S_i$ sauf les deux extrêmes, la pente entre les tailles
voisines $S_{i-1}$ et $S_{i+1}$ (une octave) :

$$
\lambda(S_i) = \frac{\log_2 c(S_{i+1}) - \log_2 c(S_{i-1})}{\log_2 S_{i+1} - \log_2 S_{i-1}}.
$$

Une pente de 0 signifie un coût indépendant de la taille ; une pente de 1, un coût
proportionnel. Une **transition** est une suite de tailles consécutives où
$\lambda > 0{,}2$.

Sur le cœur P :

1. **Séquentiel** (`stride_1`) : $c$ de 0,6 à 1,2 ns à 16 Kio, et au plus deux fois
   plus à 256 Mio, grâce au préchargement ; $D$ à 256 Mio entre 5 et 15 Gio/s (B1 :
   environ 10 Go/s au-delà de 16 Mio).
2. **Aléatoire** (`random`) : $c$ de 0,8 à 3 ns à 16 Kio (calcul de l'indice
   compris) ; au moins 30 fois plus à 256 Mio, entre 40 et 200 ns (défaut de cache et
   traduction d'adresse).
3. **Pas constants** : `stride_17` au plus 3 fois le séquentiel à 256 Mio (motif
   prévisible dans une page) ; `stride_4097` au moins la moitié du coût aléatoire à
   256 Mio (chaque accès change de page, là où les préchargeurs s'arrêtent) ;
   `stride_513` entre les deux.
4. **Transitions** de `random` : des transitions contenant ou suivant de près les
   tailles annoncées du L1d (48 Kio), du L2 (2 Mio) et du L3 (24 Mio). **Cette
   coïncidence ne suffirait pas** à attribuer une transition à un cache : c'est le
   rôle du contrôle 5.
5. **Contrôle d'attribution**, fixé à l'avance. $G$ compare une taille contenue dans
   le L2 (1 Mio) à une taille contenue dans le L3 mais pas dans le L2 (16 Mio). Si le
   L3 est responsable du palier :

   $$
   G_{\text{LP-E}} \geq 2\,G_{\text{P}},
   \qquad
   G_{\text{LP-E}} \geq 2\,G_{\text{E}},
   $$

   et, au-delà du L3, $c(256\ \text{Mio})/c(16\ \text{Mio})$ vaut au moins 2 pour P et
   E, et au plus 1,5 pour LP-E. Si ces inégalités échouent, l'attribution au L3 ne
   sera pas retenue.
6. **Lignes de cache** : $c_{\text{split}}/c_{\text{same}}$ entre 0,95 et 1,05 à
   16 Kio (tout est en L1) ; entre 1,1 et 2 à 256 Mio (deux lignes à obtenir, mais
   préchargement possible de la ligne voisine).
7. **Contrôles** : $c_{\text{bis}}/c_1$ entre 0,97 et 1,03 par processus (médiane sur
   les tailles) ; $T_{\text{double}}/T_1$ entre 1,8 et 2,2.
8. **Cœurs** : à 16 Kio, E et LP-E plus lents que P d'un facteur 1,2 à 2,5 (calcul
   plus lent, d'après A2) ; écarts relatifs plus faibles à 256 Mio, où l'attente de la
   mémoire domine.

## 4. Code et parties importantes

- [`src/traversal.c`](src/traversal.c), compilé par GCC `-O2` : parcours, références
  indépendantes, plan des mesures construit avant la première mesure, vérification de
  chaque résultat après la phase de mesure, `AnonHugePages` relevé dans
  `/proc/self/smaps_rollup`.
- [`prepare.py`](prepare.py), [`run.sh`](run.sh) : topologie des caches, plan des
  processus mélangé, épinglage.
- [`verify.py`](verify.py) : complétude, épinglage, pages de 4 Kio, exactitude,
  recalcul en Python.
- [`analyze.py`](analyze.py) : résumés, pentes locales, contrôle d'attribution et
  figures selon [`STYLE_FIGURES.md`](../../STYLE_FIGURES.md).

Le processus demande `MADV_NOHUGEPAGE` pour le tableau : pages de 4 Kio, sans toucher
au réglage global (`transparent_hugepage` en mode `madvise`). Le tableau est alloué et
entièrement écrit avant la première mesure, pour qu'aucun défaut de page n'ait lieu
pendant la mesure.

## 5. Commandes

```sh
make check      # correction, rejeu Python
make quick      # validation de la chaîne
make campaign   # campagne documentée ; refuse d'écraser data/campaign
make analyze    # résumés et figures depuis data/campaign
```

## 6. Vérification de correction, indépendante de la mesure

- `--self-test` : chaque parcours est comparé à une référence écrite autrement
  (division et produit de 128 bits explicites), pour 4 tailles et plusieurs départs.
- Pendant la campagne, hors chronométrage : chaque résultat est comparé à sa
  référence ; tout écart invalide le processus.
- `verify.py --replay` : recalcul en Python à partir de la graine, du départ et du sel
  enregistrés.
- `verify.py` : aucune page anonyme géante, conseil `MADV_NOHUGEPAGE` accepté, tous
  les échantillons pris sur le CPU prévu.

## 7. Protocole de la campagne

- 3 types de cœurs × 8 processus indépendants = 24 processus, ordre aléatoire fixé
  (graine `20260918`), épinglés sur le CPU 11, 19 ou 21.
- 9 tours par processus, le premier déclaré échauffement ; dans chaque tour, les
  297 couples (mesure, taille) dans un ordre tiré au hasard.
- Aucun défaut de page attendu pendant la mesure (vérifié par `getrusage`).
- Unité statistique : le processus ; $c$ est la médiane sur 8 tours. Débit : 8 octets
  par accès, 16 pour les paires.
- Entre processus : médiane et IC 95 % bootstrap percentile.
- Pentes locales et rapports de la prédiction 5 : sur les médianes entre processus.
  Rapports des prédictions 6 et 7 : par processus, puis résumés.
- Aucun réglage global de la machine ; préchargeurs actifs (état par défaut).

## 8. Données brutes

- [`data/campaign/`](data/campaign/) : `plan.csv` (écrit avant la mesure),
  `topology.csv` (type de cœur et caches annoncés par CPU), un fichier `run-NNN.csv`
  par processus (une ligne par échantillon : parcours, taille, nombre d'accès,
  départ, sel, durée, CPU, résultat, référence) et `run-NNN-meta.csv` (conseil
  `MADV_NOHUGEPAGE`, `AnonHugePages`, fréquence, `getrusage`).
- [`data/environment-campaign.txt`](data/environment-campaign.txt) : machine, caches
  (`lscpu -C`), pages géantes transparentes, empreintes SHA-256.
- Résumés : `reports/campaign-costs.csv` ($c$ et $D$ par cœur, parcours et taille, y
  compris `stride_513`, non tracé), `-transitions.csv`, `-attribution.csv`,
  `-controls.csv`.

Les 64 152 échantillons (24 processus × 9 tours × 297 mesures) ont un résultat exact ;
aucune page géante n'a été utilisée ; au plus 12 défauts de page mineurs par
processus pendant la mesure. Aucune observation retirée.

## 9. Figures

- [`figures/campaign-patterns.pdf`](figures/campaign-patterns.pdf) : cœur P ; $c$ (a)
  et $D$ (b) selon $S$, pour le parcours séquentiel, deux pas constants et
  l'aléatoire ; bandes : écart interquartile entre processus ; repères : tailles de
  cache **annoncées**, pas mesurées.
- [`figures/campaign-cores.pdf`](figures/campaign-cores.pdf) : cœurs P, E et LP-E ; $c$
  des accès aléatoires (a) et sa pente locale $\lambda$ (b), débit séquentiel (c),
  rapport $c_{\text{split}}/c_{\text{same}}$ (d).

Les deux axes du panneau (a) sont logarithmiques : une droite de pente 1 y signifie
un coût proportionnel à la taille, un palier un coût indépendant de la taille.

## 10. Résultats observés et interprétation

Chiffres de la campagne, médianes entre 8 processus par cœur.

### 10.1 Cœur P : quatre ordres d'accès, mêmes données

| $c$ en ns par accès | 16 Kio | 1 Mio | 2 Mio | 16 Mio | 256 Mio | $c(256\ \text{Mio})/c(16\ \text{Kio})$ |
|---|---:|---:|---:|---:|---:|---:|
| `stride_1` (séquentiel) | 1,36 | 1,39 | 1,48 | 1,94 | 2,13 | 1,6 |
| `stride_17` | 1,36 | 1,43 | 1,71 | 5,62 | 8,69 | 6,4 |
| `stride_513` | 1,38 | 1,62 | 1,88 | 7,78 | 12,32 | 8,9 |
| `stride_4097` | 1,41 | 1,53 | 1,58 | 6,65 | 7,47 | 5,3 |
| `random` | 1,23 | 1,33 | 1,95 | 10,34 | 16,77 | 13,6 |

- **Tant que les données tiennent dans 1 Mio, l'ordre des accès ne change rien** :
  1,1 à 1,6 ns partout ; c'est le calcul de l'indice qui domine.
- À 256 Mio, le même accès coûte 2,1 ns en séquentiel et 16,8 ns en aléatoire : la
  localité vaut un facteur 8.
- **Prédiction 1 réfutée pour le débit** : $D$ vaut 5,5 Gio/s à 16 Kio et 3,5 Gio/s à
  256 Mio, au lieu de 5 à 15 Gio/s. Le séquentiel coûte déjà 1,36 ns dans le cache
  (prédit 0,6 à 1,2) : c'est la boucle (avance de l'indice par `add`, `cmp`,
  `cmovae`, puis addition) qui limite, pas la mémoire. B1 lisait plus vite (environ
  10 Go/s au-delà de 16 Mio) avec une boucle plus simple ; **ce montage ne mesure donc
  pas la bande passante de la mémoire vive**. Le coût séquentiel n'augmente que de
  60 % entre 16 Kio et 256 Mio, ce qui reste conforme au « au plus deux fois ».
- **Prédiction 2 réfutée** : l'aléatoire coûte 16,8 ns à 256 Mio (prédit 40 à 200 ns)
  et seulement 13,6 fois son coût à 16 Kio (prédit au moins 30 fois). Interprétation :
  les indices ne dépendent pas des valeurs lues, donc le processeur lance plusieurs
  lectures à la fois et plusieurs défauts de cache se recouvrent. **Un parcours
  aléatoire indépendant mesure un débit de défauts, pas la latence d'un accès.** Si un
  accès isolé à la mémoire vive dure de l'ordre de 80 à 100 ns (ordre de grandeur
  courant, non mesuré ici), il en faudrait 5 à 6 en parallèle ; C2, avec des accès
  dépendants qui interdisent ce recouvrement, le mesurera.
- **Prédiction 3 partiellement réfutée** : `stride_17` coûte 8,7 ns à 256 Mio,
  4,1 fois le séquentiel (prédit au plus 3) ; `stride_4097` coûte 7,5 ns, soit
  0,45 fois l'aléatoire (prédit au moins 0,5), et **moins** que `stride_513`
  (12,3 ns). Aux grandes tailles, `stride_4097` alterne entre 6,8 et 8,0 ns d'une
  demi-octave à l'autre, sans explication établie.

### 10.2 Transitions : le contrôle d'attribution échoue

Transitions détectées sur `random` ($\lambda > 0{,}2$) :

| Cœur | Caches annoncés | Transition | Pente maximale |
|---|---|---|---|
| P | L1d 48 Kio, L2 2 Mio, L3 24 Mio | de 1 à 24 Mio | 1,12 vers 6 Mio |
| E | L1d 32 Kio, L2 2 Mio, L3 24 Mio | de 1 à 48 Mio | 0,99 vers 12 Mio |
| LP-E | L1d 32 Kio, L2 2 Mio, pas de L3 | de 512 Kio à 3 Mio | 2,54 vers 1,5 Mio |

Des pentes isolées à peine au-dessus du seuil apparaissent aussi (E à 96 Mio, LP-E à
8 Mio et de 128 à 192 Mio).

- **Aucune transition près du L1d**, sur aucun cœur : de 4 à 256 Kio, le coût
  aléatoire reste plat (1,1 à 1,2 ns sur P). Prédiction 4 réfutée pour le L1d : si le
  passage du L1 au L2 a un coût, il est invisible à côté du calcul de l'indice.
- **Le contrôle fixé à l'avance échoue** :

| Cœur | $G$ (médiane par processus, IC 95 %) | $c(256\ \text{Mio})/c(16\ \text{Mio})$ |
|---|---|---:|
| P | 7,90 [7,39 ; 8,33] | 1,62 |
| E | 6,24 [5,47 ; 6,35] | 1,89 |
| LP-E | 10,97 [10,57 ; 11,21] | 1,66 |

  $G_{\text{LP-E}}/G_{\text{P}} = 1{,}38$ et $G_{\text{LP-E}}/G_{\text{E}} = 1{,}77$,
  sous le seuil de 2 ; au-delà de 16 Mio, les rapports de P et E restent sous 2 et
  celui de LP-E dépasse 1,5. **Les trois inégalités échouent : conformément au
  protocole, l'attribution d'un palier au L3 n'est pas retenue.**
- **Lecture exploratoire**, décidée après avoir vu les courbes : la forme diffère
  nettement. Entre 1 et 2 Mio, le coût aléatoire est multiplié par 5,8 sur le cœur
  LP-E contre 1,5 sur P et 1,4 sur E ; P et E montent ensuite progressivement
  jusqu'à 24 à 48 Mio. C'est compatible avec l'absence de L3 sur le cœur LP-E, mais le
  critère $G$ (1 Mio contre 16 Mio) ne capte pas cette différence, parce que P et E ont
  aussi fortement augmenté à 16 Mio. Une explication alternative sérieuse : avec des
  pages de 4 Kio, la TLB de second niveau ne couvre plus les données au-delà de
  quelques Mio (hypothèse, capacité non vérifiée ici), si bien que traductions
  d'adresses et défauts de cache se superposent précisément dans cette zone. C2
  séparera les deux effets avec des pages géantes.

### 10.3 Débit séquentiel et différences entre cœurs

| Cœur | `stride_1` à 16 Kio | à 256 Mio | `random` à 16 Kio | à 256 Mio |
|---|---:|---:|---:|---:|
| P | 1,36 ns (5,5 Gio/s) | 2,13 ns (3,5 Gio/s) | 1,23 ns | 16,8 ns |
| E | 2,13 ns (3,5 Gio/s) | 2,52 ns (3,0 Gio/s) | 1,97 ns | 26,8 ns |
| LP-E | 1,73 ns (4,3 Gio/s) | 2,55 ns (2,9 Gio/s) | 1,60 ns | 46,6 ns |

- Dans le cache, E et LP-E sont 1,3 à 1,6 fois plus lents que P ; prédiction 8
  confirmée pour ce point.
- À 256 Mio, l'écart **se réduit** en séquentiel (1,2 fois) mais **pas** en aléatoire :
  le cœur LP-E y est 2,8 fois plus lent que P. Prédiction 8 réfutée pour l'aléatoire.
  C'est cohérent avec 10.1 : si le coût aléatoire dépend du nombre de défauts traités
  en parallèle, il dépend des ressources du cœur, pas seulement de la mémoire.
- Le débit séquentiel du cœur LP-E chute dès 2 Mio (4,0 à 3,1 Gio/s), celui de P et E
  plus progressivement.

### 10.4 Lignes de cache

$c_{\text{split}}/c_{\text{same}}$, médiane par processus :

| Cœur | 16 Kio | 256 Mio |
|---|---:|---:|
| P | 1,17 | 1,32 |
| E | 1,04 | 1,60 |
| LP-E | 1,05 | 2,30 |

- Aux grandes tailles, lire 16 octets à cheval sur deux lignes coûte 1,3 à 2,3 fois
  plus que dans une seule ligne, alors que l'instruction est la même (une lecture de
  16 octets) : **la quantité lue ne suffit pas, son alignement sur les lignes
  compte**. Prédiction 6 confirmée pour P et E, réfutée pour LP-E (2,30, au-dessus de
  2) et pour P à 16 Kio (1,17 alors que tout est dans le cache).
- Entre 4 et 16 Mio sur P, le rapport tombe sous 1 (jusqu'à 0,8) : inexpliqué.

### 10.5 Contrôles et qualité

- A/A ($c_{\text{bis}}/c_1$) : P de 0,980 à 1,034, E de 0,998 à 1,001, LP-E de 0,997 à
  1,007. Prédiction 7 confirmée, sauf un processus P à 1,034.
- Contrôle positif ($T_{\text{double}}/T_1$) : 1,953 à 2,016.
- Changements de contexte involontaires : jusqu'à 221 (P), 487 (E) et 1 355 (LP-E)
  par processus. La campagne a duré 19,5 minutes pour 24 processus (environ 49 s par
  processus en moyenne, vérification comprise), avec une charge moyenne de 1,61 au
  départ, plus élevée que pour les projets précédents.

### 10.6 Ce que C1 permet et ne permet pas de conclure

Permet de conclure, sur cette machine :

- l'ordre des accès ne compte pas tant que les données tiennent dans environ 1 Mio, et
  compte d'un facteur 8 à 256 Mio sur le cœur P ;
- un parcours aléatoire à indices indépendants n'est pas une mesure de latence : il
  mesure ce que le cœur sait paralléliser, d'où des écarts entre cœurs qui ne se
  réduisent pas avec la taille ;
- l'alignement d'une lecture sur les lignes de cache change son coût, jusqu'à 2,3 fois ;
- une coïncidence entre une transition et une taille de cache annoncée ne suffit pas :
  le contrôle fixé à l'avance a échoué.

Ne permet pas de conclure :

- la bande passante de la mémoire vive (la boucle séquentielle limite) ;
- la latence d'un accès à la mémoire vive ;
- quel niveau de cache, ou la TLB, produit chaque transition.

Pour les 13 ms : à 17 ns par accès aléatoire sur le cœur P, il faudrait environ
800 000 accès lointains pour atteindre 13 ms ; un traitement de requête simple n'en
fait vraisemblablement pas autant, mais c'est à vérifier sur le code d'origine plutôt
qu'à supposer.

## 11. Limites et expériences suivantes

- Un CPU par type de cœur, une campagne ; charge de fond plus élevée que pour les
  projets précédents et nombreux changements de contexte sur E et LP-E.
- Pages de 4 Kio uniquement : traductions d'adresses et caches non séparés.
- Préchargeurs matériels actifs et non contrôlables sans droits d'administration.
- Tailles de cache annoncées par le noyau, jamais mesurées ; cache L3 partagé avec les
  autres processus de la machine.
- Boucle séquentielle trop lente pour atteindre la limite de la mémoire vive.

Expériences suivantes :

1. **C2, accès dépendants** : parcours de liste chaînée, où chaque adresse dépend de la
   valeur précédente, pour mesurer la latence ; pages de 4 Kio contre pages géantes de
   2 Mio (réglage par processus, `MADV_HUGEPAGE`), pour séparer TLB et caches ;
   défauts de page.
2. Bande passante : reprendre la somme la plus simple de B1 (sans indice modulo) ou une
   copie `memcpy` de grands blocs, pour atteindre la limite de la mémoire vive.
3. Avec votre accord seulement : compteurs `dTLB-load-misses` et `cache-misses` pour
   confirmer ou réfuter les lectures de 10.1 et 10.2.

## 12. Compréhension et prolongement

Questions :

1. Pourquoi le coût d'un accès aléatoire (16,8 ns à 256 Mio) peut-il être très
   inférieur à la latence d'un accès à la mémoire vive ? Qu'est-ce qui, dans le code,
   le permet ?
2. Pourquoi aucune transition n'apparaît-elle au niveau du cache L1d ?
3. Le contrôle d'attribution a échoué alors que les courbes « ressemblent » à ce qu'on
   attendait. Que faut-il retenir de cet échec pour présenter une courbe de ce type à
   un superviseur ?
4. Pourquoi une lecture de 16 octets coûte-t-elle plus cher à cheval sur deux lignes,
   et pourquoi l'écart dépend-il du cœur ?
5. Pourquoi ce montage ne mesure-t-il pas la bande passante de la mémoire, et comment
   le modifier pour qu'il la mesure ?

Prolongement : écrire une version de `walk_random` qui lit **quatre** éléments
aléatoires indépendants par itération. Prédire, avant de mesurer, son coût par accès à
256 Mio sur les cœurs P et LP-E, puis comparer : le coût par accès baisse-t-il,
reste-t-il stable ou augmente-t-il, et qu'en conclure sur le nombre de défauts traités
en parallèle ?
