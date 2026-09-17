# C2 - Accès dépendants : latence, TLB et défauts de page

## 1. Question et prérequis

**Question :** combien coûte vraiment un accès lointain à la mémoire quand le
processeur ne peut pas en lancer plusieurs à la fois ? Quelle part de ce coût revient
à la traduction d'adresses plutôt qu'aux caches, et combien coûte le premier accès à
une mémoire neuve ?

Prérequis : [C1](../05-memory-traversal/README.md), dont ce projet reprend trois
questions laissées ouvertes : des accès aléatoires indépendants qui coûtent bien moins
que la latence attendue (hypothèse : défauts de cache traités en parallèle), un
contrôle d'attribution au cache L3 qui a échoué, et une explication concurrente par la
TLB avec des pages de 4 Kio. Le protocole est celui d'A2 à C1.

## 2. Notions nécessaires

**Intuition.** Dans une chasse au trésor où chaque indice donne l'emplacement du
suivant, personne ne peut chercher deux indices à la fois. Avec une liste de courses,
on peut envoyer plusieurs personnes en même temps.

- **Accès dépendants** (*pointer chasing*) : l'adresse d'un accès est la valeur lue au
  précédent. Le processeur doit attendre la fin de chaque accès pour lancer le
  suivant : la durée mesurée approche la **latence** d'un accès.
- **Adresse virtuelle, adresse physique** (*virtual*, *physical address*) : le
  programme manipule des adresses virtuelles, traduites en adresses physiques par une
  **table des pages** (*page table*) à plusieurs niveaux.
- **TLB** (*translation lookaside buffer*) : cache des traductions récentes. **Défaut
  de TLB** (*TLB miss*) : la traduction est absente, et le processeur parcourt la
  table des pages (*page walk*), ce qui demande d'autres accès mémoire.
- **Page géante** (*huge page*) : page de 2 Mio au lieu de 4 Kio. Une entrée de TLB
  couvre alors 512 fois plus de mémoire, et la table des pages a un niveau de moins à
  parcourir.
- **Défaut de page** (*page fault*) : premier accès à une page virtuelle sans page
  physique ; le noyau alloue une page, la **met à zéro**, puis met à jour la table.
  **Défaut mineur** (*minor fault*) : sans lecture sur disque.
- **Pages géantes transparentes** (*transparent huge pages*, THP) : le noyau fournit
  des pages de 2 Mio sans configuration préalable. En mode `madvise` (celui de cette
  machine), un processus les demande pour une zone avec `madvise(MADV_HUGEPAGE)`. Le
  noyau **peut refuser** s'il ne trouve pas de bloc physique contigu de 2 Mio.
- **Cycle de Sattolo** (*Sattolo's algorithm*) : permutation aléatoire formant un seul
  cycle ; partir de n'importe quel élément visite tous les autres avant de revenir.

### Notations

**Données.** Pour chaque taille $S$ de 4 Kio à 256 Mio (par octaves, 17 tailles), deux
tableaux de $N = S/8$ successeurs, chacun dans sa propre zone alignée sur 2 Mio :
$\operatorname{succ}(i)$ donne l'indice qui suit $i$.

- **Cycle aléatoire** : $\operatorname{succ}$ est un cycle de Sattolo.
- **Liste séquentielle** : $\operatorname{succ}(i) = i + 1$.

**Mesures :**

| Mesure (nom dans les données) | Ce qu'elle exécute | Accès par échantillon | Rôle |
|---|---|---:|---|
| `chase_random` | $i \leftarrow \operatorname{succ}(i)$ dans le cycle aléatoire | $2^{18}$ | accès dépendants dispersés : latence |
| `chase_random_double` | idem | $2^{19}$ | contrôle positif : durée attendue × 2 |
| `chase_sequential` | $i \leftarrow \operatorname{succ}(i)$ dans la liste séquentielle | $2^{18}$ | accès dépendants mais contigus |
| `independent_random` | lecture d'éléments d'indices aléatoires, calculés sans rien lire, dans le même tableau | $2^{20}$ | accès indépendants dispersés, comme en C1 |
| `independent_random_bis` | idem | $2^{20}$ | contrôle A/A : rapport vrai 1 |
| `page_fault_touch` | zone neuve de 16 Mio ou 256 Mio : écriture d'un octet par pas de 4 Kio (premier accès), puis seconde écriture de chaque page (second accès) | | coût d'un défaut de page |

**Facteurs croisés**, fixés **par processus** :

- **Taille de page** demandée pour toutes les zones : 4 Kio (`MADV_NOHUGEPAGE`) ou
  2 Mio (`MADV_HUGEPAGE`). Aucun réglage global n'est modifié.
- **Cœur** : P (CPU 11 ; caches annoncés L1d 48 Kio, L2 2 Mio, L3 24 Mio) ou LP-E
  (CPU 21 ; L1d 32 Kio, L2 2 Mio, **pas de L3**).

**Symboles :**

| Symbole | Signification | Unité |
|---|---|---|
| $S$ | taille des données | Kio, Mio |
| $c(S)$ | coût par accès : durée de l'échantillon divisée par le nombre d'accès ; médiane des tours mesurés dans un processus | ns |
| $c_{\text{dep}}/c_{\text{ind}}$ | rapport de `chase_random` à `independent_random` : **facteur de recouvrement** | |
| $c_{\text{seq}}$ | coût de `chase_sequential` | ns |
| $c_{4\text{K}}/c_{2\text{M}}$ | rapport du coût en pages de 4 Kio au coût en pages de 2 Mio, même cœur, même mesure | |
| $G$ | critère d'attribution de C1 : $G = c(16\ \text{Mio}) / c(1\ \text{Mio})$ | |
| $t_1$, $t_2$ | durée du premier et du second accès d'une zone neuve | µs |
| $f$ | nombre de défauts de page pendant le premier accès, compté par `getrusage` | |
| $c_{\text{bis}}/c_{\text{ind}}$ | contrôle A/A | |
| $T_{\text{double}}/T$ | contrôle positif : durée de `chase_random_double` sur durée de `chase_random` | |

Ce qui est **garanti** : les valeurs lues et le parcours complet du cycle (vérifiés).
Ce qui **est demandé** mais pas garanti : les pages géantes (part obtenue mesurée pour
chaque processus et chaque zone). Ce qui **dépend de la machine** : latences, taille
des TLB, coût de mise à zéro. Aucun compteur de défauts de TLB ou de cache n'est
accessible (`perf_event_paranoid=4`) ; seuls les défauts de page sont comptés.

## 3. Prédictions, écrites avant la campagne

### 3.1 Code machine du parcours dépendant

```asm
; chase, GCC -O2 : la seule chaîne portée par la boucle passe par la lecture
add    rax, 0x1
add    rdx, rsi
mov    rsi, QWORD PTR [rdi+rsi*8]   ; indice suivant = valeur lue
cmp    rcx, rax
jne    <chase+0x10>
```

L'indice suivant **est** la valeur lue : aucune lecture ne peut commencer avant la fin
de la précédente.

### 3.2 Transparence

Pendant la mise au point, deux processus de réglage (cœur P, 4 Kio et 2 Mio, 2 tours
dont 1 mesuré, $2^{20}$ accès dépendants) ont servi à dimensionner la campagne. Leur
durée totale par mesure a été regardée ; elle donne ces **moyennes agrégées**, connues
avant d'écrire ce qui suit :

- `chase_random`, tailles de 32 à 256 Mio : environ 400 ns par accès en 4 Kio, 360 ns
  en 2 Mio ; tailles de 4 Kio à 16 Mio : environ 45 et 55 ns ;
- `independent_random`, tailles de 32 à 256 Mio : environ 18 ns en 4 Kio et 15 ns en
  2 Mio ;
- défauts de page : zone de 16 Mio, 4 096 défauts en 4 Kio et 8 en 2 Mio ; zone de
  256 Mio en 2 Mio, 1 661 ou 29 255 défauts selon le tour, donc des pages géantes
  partiellement refusées ; part de pages géantes des tableaux proche de 95 %.

Les prédictions 1, 2 et 4 sont donc informées sur l'ordre de grandeur ; les autres ne
l'ont pas été.

### 3.3 Prédictions

Latence et recouvrement :

1. Cœur P, 4 Kio : $c$ de `chase_random` entre 250 et 600 ns à 256 Mio, et entre 1 et
   3 ns à 16 Kio (latence d'une lecture en L1, environ 5 cycles).
2. **Recouvrement des défauts** : $c_{\text{dep}}/c_{\text{ind}}$ à 256 Mio entre 10 et
   40 sur le cœur P. Sur le cœur LP-E, qui traite vraisemblablement moins d'accès en
   parallèle, ce rapport vaut au plus 0,6 fois celui du cœur P.
3. **Dépendance sans dispersion** : $c_{\text{seq}}$ à 256 Mio au plus 3 fois son coût
   à 16 Kio, et au plus 5 % de `chase_random` : les préchargeurs reconnaissent des
   adresses contiguës même quand chacune dépend de la lecture précédente.

TLB et attribution :

4. **Pages géantes et accès indépendants**, cœur P : $c_{4\text{K}}/c_{2\text{M}}$ d'au
   moins 1,25 à 16 Mio, entre 0,9 et 1,1 jusqu'à 256 Kio. Pour `chase_random` à
   256 Mio, rapport entre 1,0 et 1,3.
5. **Contrôle d'attribution de C1, rejoué sans défauts de TLB** (pages de 2 Mio,
   `independent_random`) : l'attribution d'un palier au L3 sera retenue si
   $G_{\text{LP-E}} \geq 2\,G_{\text{P}}$, et rejetée sinon.
6. **Part de la TLB dans la transition de C1** :
   $G_{\text{P, 2 Mio}} \leq 0{,}6\ G_{\text{P, 4 Kio}}$.

Défauts de page :

7. Premier accès en 4 Kio : $t_1$ entre 0,3 et 3 µs par page (mise à zéro comprise).
   Quand les pages géantes sont obtenues, le premier accès coûte 2 à 15 fois moins
   **par Mio** qu'en 4 Kio. Dans les deux cas, $t_2 \leq 0{,}02\ t_1$.
8. Nombre de défauts : $f = S / 4\ \text{Kio}$ exactement en mode 4 Kio ; en mode
   2 Mio, au moins la moitié des zones de 16 et 256 Mio obtiennent uniquement des
   pages géantes, c'est-à-dire
   $f \leq 1{,}1 \times S / 2\ \text{Mio}$.

Contrôles :

9. $c_{\text{bis}}/c_{\text{ind}}$ entre 0,97 et 1,03 par processus (médiane sur les
   tailles) ; $T_{\text{double}}/T$ entre 1,8 et 2,2.

## 4. Code et parties importantes

- [`src/chase.c`](src/chase.c), compilé par GCC `-O2` : zones alignées et conseil de
  pages, cycles de Sattolo, parcours, premier accès, références, part de pages géantes
  lue dans `/proc/self/smaps_rollup`, défauts comptés par `getrusage`.
- [`prepare.py`](prepare.py), [`run.sh`](run.sh) : plan des processus mélangé,
  épinglage.
- [`verify.py`](verify.py) : complétude, épinglage, pages, exactitude, recalcul en
  Python des cycles et des parcours.
- [`analyze.py`](analyze.py) : résumés, contrôles fixés à l'avance et figures selon
  [`STYLE_FIGURES.md`](../../STYLE_FIGURES.md).

Les tableaux sont construits et entièrement écrits avant la première mesure : aucun
défaut de page n'a lieu pendant les parcours. Seule `page_fault_touch` utilise une
zone neuve, allouée juste avant l'échantillon.

## 5. Commandes

```sh
make check      # correction, rejeu Python
make quick      # validation de la chaîne
make campaign   # campagne documentée ; refuse d'écraser data/campaign
make analyze    # résumés et figures depuis data/campaign
```

## 6. Vérification de correction, indépendante de la mesure

- `--self-test` : un cycle de Sattolo visite exactement $N$ éléments avant de revenir,
  pour 6 tailles ; parcours et références identiques ; liste séquentielle exacte ;
  écriture d'une page par pas de 4 Kio.
- Pendant la campagne, hors chronométrage : chaque résultat est comparé à une
  référence ; après chaque premier accès, le contenu de chaque page est vérifié.
- `verify.py --replay` : cycles et parcours recalculés en Python.
- `verify.py` : aucune page géante en mode 4 Kio ; part de pages géantes rapportée en
  mode 2 Mio, processus invalide sous 50 %.

## 7. Protocole de la campagne

- 2 cœurs × 2 tailles de page × 8 processus indépendants = 32 processus, ordre
  aléatoire fixé (graine `20260919`), épinglés sur le CPU 11 ou 21.
- 11 tours par processus, le premier déclaré échauffement ; dans chaque tour, les
  87 mesures (85 d'accès, 2 de défauts de page) dans un ordre tiré au hasard.
- Unité statistique : le processus ; médiane sur 10 tours de $c$, ou du coût par page
  pour les défauts. Entre processus : médiane et IC 95 % bootstrap percentile.
- Rapports entre mesures (prédictions 2, 3, 9) : par processus, puis résumés.
  Rapports entre tailles de page (4 à 6) : les processus diffèrent d'une taille de
  page à l'autre, donc rapport des médianes de deux groupes indépendants, avec
  intervalle bootstrap du rapport.
- Défauts de page : un échantillon en mode 2 Mio est classé « pages géantes
  obtenues » si $f \leq 1{,}1 \times S / 2\ \text{Mio}$ ; les coûts sont résumés
  séparément selon ce classement.
- Aucun réglage global de la machine.

## 8. Données brutes

- [`data/campaign/`](data/campaign/) : `plan.csv` (écrit avant la mesure),
  `topology.csv`, un fichier `run-NNN.csv` par processus (une ligne par échantillon :
  mesure, taille, accès, départ, sel, $t_1$ et $t_2$, défauts de page, CPU, résultat,
  référence) et `run-NNN-meta.csv` (taille de page demandée, part de pages géantes
  obtenue, changements de contexte).
- [`data/environment-campaign.txt`](data/environment-campaign.txt) : machine, caches,
  compteurs `thp_*` du noyau, empreintes SHA-256.
- Résumés : `reports/campaign-costs.csv`, `-overlap.csv`
  ($c_{\text{dep}}/c_{\text{ind}}$ et contigus sur dispersés), `-pages.csv`
  ($c_{4\text{K}}/c_{2\text{M}}$), `-attribution.csv` et `-attribution-tests.csv`,
  `-faults.csv`, `-controls.csv`.

Les 30 624 échantillons (32 processus × 11 tours × 87 mesures) ont un résultat exact.
Tous les processus en mode 2 Mio ont obtenu 100 % de pages géantes pour leurs tableaux
et pour chaque zone neuve. Aucune observation retirée.

## 9. Figures

- [`figures/campaign-latency.pdf`](figures/campaign-latency.pdf) : $c$ selon $S$ pour
  les accès dépendants dispersés, indépendants dispersés et dépendants contigus ;
  cœur P (a) et cœur LP-E (b) ; trait plein : pages de 4 Kio, tirets : pages de
  2 Mio.
- [`figures/campaign-overlap-tlb.pdf`](figures/campaign-overlap-tlb.pdf) :
  $c_{\text{dep}}/c_{\text{ind}}$ (a) ; $c_{4\text{K}}/c_{2\text{M}}$ pour les accès
  indépendants (b) et dépendants (c) ; contrôle d'attribution $G$ (d), un point par
  processus.
- [`figures/campaign-faults.pdf`](figures/campaign-faults.pdf) : coût du premier accès
  à une zone neuve, par Mio, selon la taille de page.

## 10. Résultats observés et interprétation

Médianes entre 8 processus par condition.

### 10.1 La latence d'un accès lointain : environ 400 ns

| $c$ en ns par accès | 16 Kio | 64 Kio | 1 Mio | 2 Mio | 4 Mio | 16 Mio | 256 Mio |
|---|---:|---:|---:|---:|---:|---:|---:|
| P, `chase_random`, 4 Kio | 2,9 | 5,0 | 26,7 | 56,5 | 144 | 347 | 455 |
| P, `chase_random`, 2 Mio | 2,9 | 5,1 | 23,5 | 49,4 | 182 | 344 | 406 |
| LP-E, `chase_random`, 4 Kio | 1,9 | 7,1 | 34,4 | 95,0 | 236 | 354 | 433 |
| LP-E, `chase_random`, 2 Mio | 1,9 | 6,9 | 29,8 | 62,4 | 229 | 348 | 384 |
| P, `independent_random`, 4 Kio | 1,5 | 1,4 | 2,3 | 3,9 | 7,0 | 18,9 | 29,2 |
| LP-E, `independent_random`, 4 Kio | 1,8 | 1,8 | 2,8 | 15,9 | 22,2 | 29,2 | 49,5 |
| P, `chase_sequential`, 4 Kio | 2,9 | 2,7 | 3,3 | 3,9 | 3,8 | 3,8 | 4,0 |

- **Quand le processeur doit attendre chaque accès, un accès lointain coûte 380 à
  455 ns**, presque autant sur le cœur LP-E que sur le cœur P : c'est une propriété de
  la mémoire, pas du cœur. Prédiction 1 confirmée (250 à 600 ns ; 2,9 ns à 16 Kio,
  dans l'intervalle de 1 à 3 ns).
- Cette latence vaut **environ 4 fois l'ordre de grandeur de 80 à 100 ns cité en C1**
  sans avoir été mesuré. Le type de mémoire vive et sa gestion d'énergie ne sont pas
  identifiables sans droits d'administration (`dmidecode`) : l'origine de cette valeur
  élevée reste une question ouverte.
- **Recouvrement des défauts** : à 256 Mio, $c_{\text{dep}}/c_{\text{ind}}$ vaut 15,6
  (4 Kio) à 20,5 (2 Mio) sur le cœur P, et 8,8 à 12,1 sur le cœur LP-E. Le cœur P
  traite donc une vingtaine de défauts de cache à la fois, le cœur LP-E une dizaine.
  Prédiction 2 confirmée (10 à 40 ; rapport LP-E sur P de 0,56 et 0,59, au plus 0,6).
  L'hypothèse de C1 est confirmée dans son principe, avec un facteur de recouvrement
  bien plus grand que les 5 à 6 supposés.
- **Dépendance sans dispersion** : $c_{\text{seq}}$ vaut 4,0 ns à 256 Mio (1,4 fois son
  coût dans le cache) et 0,9 % de `chase_random`. Prédiction 3 confirmée : la
  dépendance seule ne coûte presque rien si les adresses sont prévisibles pour les
  préchargeurs.
- **Lecture exploratoire** : les accès dépendants font apparaître une transition entre
  32 et 64 Kio, plus forte sur le cœur LP-E (1,9 à 7,1 ns, L1d annoncé 32 Kio) que sur
  le cœur P (3,4 à 5,0 ns, L1d annoncé 48 Kio). C1, avec des accès indépendants, n'en
  voyait aucune. C'est compatible avec le L1d, sans test fixé à l'avance.
- Dans le cache, le cœur P coûte **plus** que le cœur LP-E pour les accès dépendants
  (2,9 contre 1,9 ns) : inexpliqué.

### 10.2 TLB et caches : les deux attributions échouent

| $c_{4\text{K}}/c_{2\text{M}}$ | 256 Kio | 1 Mio | 16 Mio | 256 Mio |
|---|---:|---:|---:|---:|
| P, `independent_random` | 1,00 | 0,93 | 1,22 | 1,45 |
| LP-E, `independent_random` | 1,02 | 1,06 | 1,05 | 1,56 |
| P, `chase_random` | 1,14 | 1,14 | 1,01 | 1,12 |
| LP-E, `chase_random` | 1,07 | 1,16 | 1,02 | 1,13 |

- À 256 Mio, les pages géantes réduisent le coût des accès lointains de 11 à 36 %
  (rapports de 1,12 à 1,56), surtout pour les accès indépendants. Prédiction 4 :
  rapport de 1,22 à 16 Mio sur le cœur P, **juste sous** le seuil de 1,25 ; rapports
  de 0,88 et 0,89 à 16 et 64 Kio, **juste hors** de l'intervalle 0,9 à 1,1 ; accès
  dépendants à 256 Mio : 1,12, dans l'intervalle. Prédiction partiellement réfutée.
- **Contrôle d'attribution au L3, rejoué en pages de 2 Mio** :
  $G_{\text{LP-E}}/G_{\text{P}} = 1{,}61$ pour les accès indépendants et 0,81 pour les
  dépendants, sous le seuil de 2. **Prédiction 5 : attribution au L3 de nouveau
  rejetée.**
- **Part de la TLB dans la transition de C1** :
  $G_{\text{P, 2 Mio}}/G_{\text{P, 4 Kio}} = 0{,}80$ (indépendants) et 1,11
  (dépendants), au-dessus du seuil de 0,6. **Prédiction 6 réfutée** : la TLB n'explique
  qu'une petite part de la montée entre 1 et 16 Mio.
- Ce que les données montrent vraiment, en lecture exploratoire : avec des pages de
  2 Mio, la montée la plus forte des accès dépendants se produit entre 2 et 4 Mio **sur
  les deux cœurs** (facteur 3,7), dont le L2 annoncé est de 2 Mio ; et à 4 et 16 Mio,
  le cœur P, qui a un L3 de 24 Mio, n'est pas plus rapide que le cœur LP-E, qui n'en a
  pas (344 contre 348 ns à 16 Mio). Deux hypothèses restent ouvertes : le L3, partagé
  par 20 CPU logiques et par tous les programmes de la machine, ne garde pas nos
  16 Mio ; ou son accès aléatoire est lui-même proche de celui de la mémoire vive sur
  ce processeur.
- Deux anomalies non expliquées : à 4 Mio sur le cœur P, les pages de 4 Kio sont plus
  rapides que celles de 2 Mio (rapport 0,79 pour les dépendants, 0,73 pour les
  indépendants) ; à 2 Mio sur le cœur LP-E, les accès indépendants coûtent 2,8 fois
  plus en 4 Kio qu'en 2 Mio.

### 10.3 Défauts de page : environ 2 µs par page de 4 Kio

| Premier accès | P, 4 Kio | P, 2 Mio | LP-E, 4 Kio | LP-E, 2 Mio |
|---|---:|---:|---:|---:|
| $t_1$ par Mio, zone de 16 Mio (µs) | 505 | 175 | 616 | 264 |
| $t_1$ par Mio, zone de 256 Mio (µs) | 461 | 130 | 632 | 264 |
| $f$, zone de 256 Mio | 65 536 | 128 | 65 536 | 128 |
| $t_2/t_1$ | 1,1 à 2,4 % | 2,9 à 4,4 % | 1,9 % | 4,3 à 4,6 % |

- En pages de 4 Kio, un défaut de page (mise à zéro comprise) coûte 1,8 à 2,0 µs sur
  le cœur P et 2,4 à 2,5 µs sur le cœur LP-E. Prédiction 7 confirmée pour ce point
  (0,3 à 3 µs).
- Les pages géantes rendent le premier accès 2,3 à 3,5 fois moins cher par Mio, dans
  l'intervalle prédit (2 à 15).
- $t_2/t_1$ vaut 1 à 5 % : le défaut domine, mais la prédiction $t_2 \leq 0{,}02\ t_1$
  est réfutée en pages de 2 Mio (le premier accès y est moins cher, le rapport monte)
  et pour le cœur P à 256 Mio (2,4 %).
- $f$ est exactement le nombre de pages (65 536 pages de 4 Kio, ou 128 pages de 2 Mio
  pour 256 Mio). Prédiction 8 confirmée : 100 % des zones en mode 2 Mio ont obtenu des
  pages géantes pendant la campagne, alors que la mise au point en avait vu refuser
  une partie. Le noyau peut refuser : cette disponibilité dépend de l'état de la
  mémoire, pas du programme.

### 10.4 Contrôles : moins bons que dans les projets précédents

| Condition | $c_{\text{bis}}/c_{\text{ind}}$ par processus | $T_{\text{double}}/T$ (médiane, étendue) |
|---|---|---|
| P, 4 Kio | 0,948 à 1,083 | 1,80 (1,61 à 1,98) |
| P, 2 Mio | 0,969 à 1,039 | 1,92 (1,85 à 1,98) |
| LP-E, 4 Kio | 0,991 à 1,008 | 1,94 (1,92 à 1,97) |
| LP-E, 2 Mio | 0,970 à 1,005 | 1,94 (1,93 à 1,99) |

- **Prédiction 9 réfutée pour l'A/A** : il sort de 0,97 à 1,03 pour le cœur P. Le
  contrôle positif reste dans l'intervalle en médiane (1,80 à 1,94), mais il est
  **systématiquement inférieur à 2**, et un processus descend à 1,61. Doubler la
  longueur d'un parcours dépendant ne double pas tout à fait sa durée : un coût fixe
  au début de chaque parcours (état des caches ou de la TLB laissé par la mesure
  précédente, qui porte sur un autre tableau) serait amorti sur plus d'accès.
  Hypothèse non testée.
- Conséquence : les écarts de moins d'environ 10 % entre conditions (effets des pages
  géantes sur les accès dépendants, par exemple) sont à lire avec prudence ; les
  écarts d'un facteur 2 à 20 ne sont pas concernés.
- Jusqu'à 769 changements de contexte involontaires par processus ; campagne de
  30 minutes, charge moyenne de 0,47 au départ.

### 10.5 Ce que C2 permet et ne permet pas de conclure

Permet de conclure, sur cette machine :

- un accès lointain à la mémoire vive coûte environ 400 ns quand il ne peut pas être
  recouvert ; des accès indépendants en recouvrent une vingtaine sur le cœur P et une
  dizaine sur le cœur LP-E ;
- la dépendance entre accès ne coûte presque rien si les adresses restent contiguës :
  c'est la dispersion qui coûte ;
- les pages géantes réduisent le coût des accès lointains de 11 à 36 % à 256 Mio, et
  celui du premier accès par Mio d'un facteur 2,3 à 3,5 ;
- un défaut de page de 4 Kio coûte environ 2 µs.

Ne permet pas de conclure :

- quel niveau de cache produit la montée entre 1 et 16 Mio : ni le L3, ni la TLB ne
  passent les critères fixés à l'avance ;
- pourquoi la latence de la mémoire vive est si élevée ;
- le nombre réel de défauts de cache ou de TLB, faute de compteurs.

Pour les 13 ms : ils correspondent à environ 29 000 accès dépendants lointains (listes
chaînées, arbres, tables de hachage dispersées), ou à environ 6 500 défauts de page,
soit 25 Mio de mémoire neuve en pages de 4 Kio. **Une requête exécutée par un
processus neuf, qui touche pour la première fois ses structures de données, peut donc
atteindre cet ordre de grandeur** : hypothèse à vérifier en J2, en comptant les
défauts de page (`getrusage` ou `/proc/<pid>/stat`) autour de la première requête et
des suivantes.

## 11. Limites et expériences suivantes

- Deux CPU (un P, un LP-E), une campagne ; contrôles A/A et positif moins bons que pour
  les projets précédents.
- Aucun compteur matériel : défauts de cache et de TLB inférés, jamais comptés.
- Cache L3 partagé avec les autres programmes de la machine, charge non contrôlée.
- Type et configuration de la mémoire vive inconnus.
- Disponibilité des pages géantes dépendante de l'état de la mémoire : 100 % ici,
  partielle pendant la mise au point.

Expériences suivantes :

1. **D1, appels système** : coût d'entrée dans le noyau, traitement par lots ; les
   défauts de page de C2 en sont un cas particulier.
2. Contrôle positif : répéter `chase_random_double` en jetant les premiers accès de
   chaque parcours, pour tester l'hypothèse d'un coût fixe de démarrage.
3. Avec votre accord seulement : compteurs `dTLB-load-misses`, `LLC-load-misses` et
   `cycles` pour trancher entre L2, L3 et mémoire vive.
4. Pour l'enquête J2 : compter les défauts de page d'un client et d'un serveur neufs
   pendant la première requête, puis pendant les suivantes.

## 12. Compréhension et prolongement

Questions :

1. Pourquoi les accès dépendants mesurent-ils une latence, alors que les accès
   indépendants mesurent un débit ? Que révèle $c_{\text{dep}}/c_{\text{ind}}$ ?
2. Pourquoi une liste chaînée contiguë coûte-t-elle 100 fois moins qu'une liste
   dispersée, alors que chaque accès dépend du précédent dans les deux cas ?
3. Deux contrôles d'attribution ont échoué, en C1 puis en C2. Qu'est-ce que cela
   apprend sur l'interprétation d'une courbe de coût selon la taille ?
4. Pourquoi le premier accès à une zone neuve coûte-t-il moins cher par Mio avec des
   pages géantes, et dans quel cas ce choix serait-il un mauvais compromis ?
5. $T_{\text{double}}/T$ vaut 1,80 à 1,94 au lieu de 2. Proposez deux explications et
   une expérience pour les départager.

Prolongement : construire une liste chaînée dont les nœuds sont **triés par adresse
par blocs** (par exemple 64 nœuds contigus, puis un saut aléatoire). Prédire, avant de
mesurer, $c$ à 256 Mio sur le cœur P à partir des mesures de C2, puis comparer.
