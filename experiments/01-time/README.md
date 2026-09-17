# A1 - Mesurer correctement une durée sous Linux

## 1. Question et prérequis

**Question :** que signifie réellement « cette requête localhost a pris 13 ms »,
et comment vérifier que cette durée n'est pas principalement un artefact du
chronométrage ou du périmètre choisi ?

Prérequis : aucun. Compiler et exécuter un petit programme C s'apprend dans ce
projet, et aucune connaissance de l'architecture du processeur n'est supposée.

Le projet prévoit quatre contrôles. Les trois premiers sont réalisés ici ; le
quatrième demande un client et un serveur, et il est reporté à la partie J.

1. Demander au système la résolution annoncée de ses horloges.
2. Estimer le coût de deux lectures consécutives d'une horloge, et montrer
   pourquoi chronométrer une seule opération très courte est fragile.
3. Comparer temps écoulé et temps CPU, pendant un calcul puis pendant une attente.
4. Appliquer la méthode à la requête localhost, en chronométrant séparément le
   client et le serveur.

## 2. Notions nécessaires

**Intuition.** Un chronomètre placé autour d'une requête mesure un « paquet » de
travail : le code du client, d'éventuelles attentes, le noyau, le serveur et le
chronomètre lui-même peuvent tous en faire partie. Le nombre « 13 ms » ne désigne
aucun de ces composants en particulier.

**Explication technique.** Une durée est la différence entre deux lectures d'une
horloge. Sous Linux, `clock_gettime(CLOCK_MONOTONIC, ...)` lit une horloge
monotone, destinée à mesurer des intervalles. L'API garantit que cette horloge ne
recule pas ; elle ne garantit ni un coût de lecture donné, ni l'absence de
préemption, ni que le programme a utilisé le processeur pendant tout l'intervalle.

- **Temps écoulé** (*elapsed time*, *wall-clock time*) : durée entre deux instants,
  y compris les périodes où le programme ne s'exécute pas.
- **Temps CPU** (*CPU time*) : temps pendant lequel un processeur exécute le
  processus, lu ici par `CLOCK_PROCESS_CPUTIME_ID`.
- **Résolution** (*resolution*) : plus petit pas que l'horloge annonce
  (`clock_getres`). Ce n'est ni son exactitude, ni le coût d'une lecture.
- **Centile** (*percentile*) : le 95ᵉ centile d'une série est la valeur sous
  laquelle se trouvent 95 % des observations.
- **Fonction de répartition empirique** (*ECDF*) : pour chaque valeur, la fraction
  des observations qui lui sont inférieures ou égales.

### Notations

| Nom ou symbole | Signification | Unité |
|---|---|---|
| `consecutive_reads` | deux appels consécutifs à `clock_gettime(CLOCK_MONOTONIC)` ; on garde leur différence | ns |
| `batched_reads` | un lot de $b$ lectures consécutives chronométré en bloc ; on garde sa durée divisée par $b$ | ns par lecture |
| `sleep` | attente demandée de $d_{\text{attente}}$ par `clock_nanosleep` | |
| `busy_cpu` | boucle active qui calcule jusqu'à avoir consommé $d_{\text{calcul}}$ de temps CPU | |
| $t_{\text{écoulé}}$ | durée mesurée avec `CLOCK_MONOTONIC` | ns ou ms |
| $t_{\text{CPU}}$ | durée mesurée avec `CLOCK_PROCESS_CPUTIME_ID` | ns ou ms |
| $b$ | nombre de lectures par lot, $b = 10\,000$ | |
| $d_{\text{attente}}$, $d_{\text{calcul}}$ | durées demandées, 100 ms et 50 ms | ms |
| $\delta$ | dépassement de la durée demandée : $t_{\text{écoulé}} - d$ ou $t_{\text{CPU}} - d$, avec $d$ = $d_{\text{attente}}$ ou $d_{\text{calcul}}$ | µs |
| $n$ | nombre d'observations | |
| $p_{95}$ | 95ᵉ centile | |

Ce qui est **garanti** : la monotonie de `CLOCK_MONOTONIC`, et qu'une attente par
`clock_nanosleep` ne se termine pas avant la durée demandée. Ce qui **dépend de la
machine** : le coût d'une lecture d'horloge, la durée réelle des attentes, et
l'écart entre temps CPU et temps écoulé.

## 3. Modèle de coût et prédictions, écrits avant la mesure

**Modèle.** Pour une requête chronométrée côté client sur une connexion neuve, un
premier modèle décompose la durée mesurée en :

$$
T_{\text{mesuré}} = T_{\text{horloge}} + T_{\text{client}} + T_{\text{connexion}}
+ T_{\text{transport}} + T_{\text{file}} + T_{\text{serveur}} + T_{\text{retour}}
$$

où $T_{\text{horloge}}$ est le coût des lectures d'horloge, $T_{\text{client}}$ le
travail du client, $T_{\text{connexion}}$ l'établissement de la connexion,
$T_{\text{transport}}$ le passage des données par la pile réseau locale,
$T_{\text{file}}$ l'attente avant d'être servi, $T_{\text{serveur}}$ le traitement
et $T_{\text{retour}}$ le chemin de la réponse. Selon l'outil peuvent s'ajouter le
démarrage d'un processus, la résolution de nom, un proxy ou l'écriture de
journaux. Les termes ne sont pas supposés indépendants : cette somme sert d'abord
à décider quels contrôles mener.

**Ordres de grandeur.** Les conversions d'unités sont exactes :

$$
1\ \text{s} = 10^{3}\ \text{ms} = 10^{6}\ \mu\text{s} = 10^{9}\ \text{ns},
\qquad
13\ \text{ms} = 0{,}013\ \text{s} = 13\,000\ \mu\text{s} = 13\,000\,000\ \text{ns}.
$$

Convertir 13 ms en cycles de processeur exige de choisir une fréquence, et ne
prouve pas que ces cycles ont servi à la requête. À titre de calcul hypothétique,
à 3 GHz :

$$
0{,}013\ \text{s} \times 3\,000\,000\,000\ \text{Hz} = 39\,000\,000\ \text{cycles de temps écoulé}.
$$

Ce n'est pas une mesure de cycles.

**Prédictions qualitatives :**

1. Deux lectures consécutives de `CLOCK_MONOTONIC` coûteront des dizaines de ns,
   avec de la dispersion et de rares valeurs nettement plus grandes.
2. Une attente de 100 ms donnera $t_{\text{écoulé}} \geq 100$ ms environ, mais un
   $t_{\text{CPU}}$ beaucoup plus petit.
3. Pour une charge active visant 50 ms de temps CPU, $t_{\text{CPU}}$ et
   $t_{\text{écoulé}}$ seront proches, sauf préemption prolongée.
4. Les répétitions ne seront pas identiques (ordonnancement, interruptions,
   fréquence du processeur, charge concurrente).

Ces prédictions ne fixent aucune « bonne » durée universelle.

## 4. Code et parties importantes

Le programme [`src/time_lab.c`](src/time_lab.c) enchaîne quatre étapes.

- Il affiche la résolution annoncée des deux horloges (`clock_getres`).
- `consecutive_reads` : deux lectures de `CLOCK_MONOTONIC` sans rien entre elles ;
  la différence contient le coût d'une lecture et tout ce qui a pu interrompre le
  programme entre les deux.
- `batched_reads` : $b$ lectures dans une boucle, entre deux lectures encadrantes ;
  le coût fixe des deux lectures encadrantes est ainsi partagé entre $b$ lectures.
- `sleep` et `busy_cpu` : chacune est encadrée par une lecture des deux horloges,
  et leur ordre alterne à chaque répétition. `busy_cpu` interroge
  `CLOCK_PROCESS_CPUTIME_ID` toutes les 1 024 itérations pour savoir quand
  s'arrêter : c'est une charge contrôlée, pas un benchmark de calcul.

Les résultats sont écrits dans un CSV après la mesure. [`analyze.py`](analyze.py)
calcule les résumés et trace la figure.

## 5. Commandes

Depuis ce dossier :

```sh
make check       # vérification courte de correction
make quick       # contrôle rapide, environ une seconde
make campaign    # campagne documentée, environ huit secondes ici
```

Compilation exacte :

```sh
cc -O2 -std=c17 -Wall -Wextra -Wpedantic src/time_lab.c -o build/time_lab
```

Les CSV produits avant l'ajout des colonnes `sleep_target_ns` et `busy_target_ns`
exigent les options `--sleep-target-ms` et `--busy-target-ms` d'`analyze.py`.

## 6. Vérification de correction, indépendante de la mesure

`make check` vérifie que l'attente se termine sans erreur et que son
$t_{\text{écoulé}}$ atteint au moins la durée demandée. Ce sont des propriétés de
correction : aucune borne supérieure de performance n'est imposée. Le code compile
sans avertissement avec les options ci-dessus.

## 7. Protocole de la campagne

- Compilation C17 par GCC avec `-O2` ; graine `20260916`, qui fixe l'ordre
  attente puis calcul, ou l'inverse, à chaque répétition.
- $n = 50\,000$ paires `consecutive_reads`.
- $n = 50$ lots `batched_reads` de $b = 10\,000$ lectures.
- $n = 50$ attentes `sleep` de 100 ms et $n = 50$ charges `busy_cpu` de 50 ms.
- Périmètre chronométré : la préparation et l'écriture du CSV sont exclues ; pour
  `sleep` et `busy_cpu`, les quatre lectures d'horloge encadrantes sont incluses.
- Aucun cœur imposé, aucun réglage système modifié, aucun cache vidé.
- Résumés : minimum, médiane, moyenne, $p_{95}$ et maximum. Toutes les
  observations, valeurs atypiques comprises, sont conservées.

## 8. Données brutes

- [`data/campaign.csv`](data/campaign.csv) : une ligne par observation (variante,
  numéro, ordre, $t_{\text{écoulé}}$, $t_{\text{CPU}}$, graine, durées demandées,
  taille de lot).
- [`data/environment-campaign.txt`](data/environment-campaign.txt) : versions,
  topologie visible et contexte d'exécution.
- [`reports/campaign-summary.csv`](reports/campaign-summary.csv) : résumés calculés.

## 9. Figures

[`figures/campaign.pdf`](figures/campaign.pdf), selon les
[règles de style des figures](../../STYLE_FIGURES.md) :

- (a) fonction de répartition empirique des durées `consecutive_reads`, axe
  linéaire rogné à 50 ns pour montrer le corps de la distribution ; les 16 valeurs
  au-delà sont annoncées sur le panneau ;
- (b) fonction de survie $P(X \geq x)$ des mêmes durées, en échelles
  logarithmiques : elle montre toutes les valeurs, jusqu'au maximum ;
- (c) chaque répétition de `sleep` et `busy_cpu` comme un point
  $(t_{\text{CPU}}, t_{\text{écoulé}})$, avec la diagonale
  $t_{\text{écoulé}} = t_{\text{CPU}}$ ;
- (d) fonction de répartition empirique du dépassement $\delta$, en µs : temps écoulé
  et temps CPU de `busy_cpu` au-delà de 50 ms, temps écoulé de `sleep` au-delà de
  100 ms.

Sur une échelle logarithmique, deux graduations également espacées correspondent
à un même facteur multiplicatif : on voit ainsi à la fois des dizaines de ns et une
valeur atypique de plusieurs µs.

## 10. Résultats observés et interprétation

Résultats de **cette campagne uniquement** :

| Variante | Grandeur | $n$ | Minimum | Médiane | $p_{95}$ | Maximum |
|---|---|---:|---:|---:|---:|---:|
| `consecutive_reads` | $t_{\text{écoulé}}$ | 50 000 | 24 ns | 28 ns | 41 ns | 8 244 ns |
| `batched_reads` | coût par lecture | 50 | 27 ns | 27 ns | 27 ns | 28 ns |
| `busy_cpu` | $t_{\text{écoulé}}$ | 50 | 50,001 ms | 50,003 ms | 50,096 ms | 50,249 ms |
| `busy_cpu` | $t_{\text{CPU}}$ | 50 | 50,001 ms | 50,002 ms | 50,003 ms | 50,004 ms |
| `sleep` | $t_{\text{écoulé}}$ | 50 | 100,054 ms | 100,086 ms | 100,146 ms | 100,215 ms |
| `sleep` | $t_{\text{CPU}}$ | 50 | 0,018 ms | 0,027 ms | 0,037 ms | 0,039 ms |

**Résolution.** `clock_getres` annonce 1 ns pour les deux horloges. C'est une
propriété annoncée par l'API sur ce système, pas la preuve d'une mesure exacte à
1 ns.

**Temps écoulé et temps CPU répondent à deux questions différentes.** L'attente
fait progresser $t_{\text{écoulé}}$ d'environ 100 ms en ne consommant que quelques
dizaines de µs de temps CPU. Pour la charge active, les deux durées sont proches ;
les quelques surplus de $t_{\text{écoulé}}$ (maximum de 50,249 ms écoulées, alors que
$t_{\text{CPU}}$ ne dépasse pas 50,004 ms) sont compatibles avec
des interruptions ou un retrait temporaire du processeur par l'ordonnanceur.
Prédictions 2 et 3 confirmées.

**Une opération unique aussi courte que le chronomètre se mesure mal.** Les paires
de lectures ont une médiane de 28 ns (prédiction 1 confirmée), mais un maximum de
8,244 µs, conservé dans les données : un seul échantillon peut être 294 fois plus
long que la médiane. En lot, le coût par lecture reste entre 27 et 28 ns sur les
50 lots. Prédiction 4 confirmée.

**Pour les 13 ms.** 13 ms valent environ 460 000 fois la médiane de 28 ns entre deux
lectures consécutives. **La lecture de `CLOCK_MONOTONIC` ne peut donc pas expliquer
à elle seule les 13 ms** dans cet environnement. Cela n'écarte ni le démarrage d'un
outil de mesure, ni les autres termes du modèle de la section 3.

## 11. Limites et expériences suivantes

Cette expérience ne mesure ni TCP, ni HTTP, ni le programme original : elle ne peut
pas attribuer les 13 ms au réseau, au framework, au client ou au serveur. Le
processus n'était épinglé sur aucun cœur, la machine n'était pas isolée, et les
données proviennent d'une seule campagne. Le $p_{95}$ décrit 50 observations ; un
99ᵉ centile sur si peu de valeurs serait peu informatif.

Expériences suivantes : répéter la campagne dans des processus indépendants,
étudier l'effet de l'affinité (`taskset`), puis instrumenter séparément le client
et le serveur du cas localhost. `perf` pourra être essayé, mais la politique
`perf_event_paranoid=4` risque d'interdire les compteurs matériels.

## 12. Compréhension et prolongement

Questions :

1. Pourquoi une résolution annoncée de 1 ns n'implique-t-elle pas une mesure
   exacte à 1 ns ?
2. Pourquoi le temps CPU d'une attente n'est-il pas strictement nul ?
3. Que montre la valeur atypique de 8,244 µs, et que ne montre-t-elle pas ?

Prolongement : ajouter des attentes de 1, 10 et 1 000 ms et tracer le dépassement
$\delta$ selon la durée demandée, sans supposer qu'il sera constant.
