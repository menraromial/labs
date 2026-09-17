# A1 - Mesurer correctement une durée sous Linux

## 1. Question et prérequis

**Question :** que signifie réellement « cette requête localhost a pris 13 ms »,
et comment vérifier que cette durée n'est pas principalement un artefact du
chronométrage ou du périmètre choisi ?

Prérequis : savoir compiler et exécuter un petit programme C sera appris dans le
projet ; aucune connaissance de l'architecture du processeur n'est supposée.

Le projet sera découpé en quatre contrôles :

1. demander au système les résolutions de ses horloges ;
2. estimer le coût de deux lectures consécutives d'une horloge et montrer le piège
   du microbenchmark naïf ;
3. comparer temps écoulé et temps CPU pendant du calcul puis une attente ;
4. appliquer la méthode à la requête localhost, avec un chronométrage client et un
   chronométrage serveur distincts.

## 2. Notions nécessaires

Intuitivement, un chronomètre placé autour d'une requête mesure un « paquet » de
travail : le code du client, d'éventuelles attentes, le noyau, le serveur et le
coût du chronomètre peuvent tous en faire partie. Le nombre `13 ms` ne nomme pas
automatiquement l'un de ces composants.

Techniquement, une durée est la différence entre deux lectures d'horloge. Sous
Linux, `clock_gettime(CLOCK_MONOTONIC, …)` fournit une horloge monotone destinée
aux intervalles. L'API garantit la monotonie, pas un coût de lecture universel,
une absence de préemption, ni que le programme ait utilisé le CPU pendant toute
la durée.

Nous comparerons plus tard :

- `CLOCK_MONOTONIC` pour le temps écoulé ;
- `CLOCK_PROCESS_CPUTIME_ID` pour le temps CPU du processus.

Une attente volontaire devrait augmenter fortement le premier sans augmenter le
second dans la même proportion. C'est une prédiction qualitative issue du modèle,
pas encore une observation.

## 3. Modèle de coût avant mesure

Pour une mesure client d'une requête neuve, un modèle initial est :

`T_mesuré = T_lectures_horloge + T_client + T_connexion + T_transport_local + T_file_attente + T_serveur + T_retour`

Selon l'outil et son périmètre, peuvent aussi s'ajouter le démarrage d'un
processus, la résolution de nom, un proxy, l'affichage ou l'écriture de journaux.
Les termes ne sont pas supposés indépendants et cette somme sert d'abord à poser
des contrôles expérimentaux.

Conversions exactes d'unités :

- `1 s = 1 000 ms = 1 000 000 µs = 1 000 000 000 ns` ;
- `13 ms = 0,013 s = 13 000 µs = 13 000 000 ns`.

Convertir 13 ms en cycles exige une fréquence choisie et ne prouve pas que ces
cycles ont été consacrés à la requête. À titre de **calcul hypothétique**, à
3 GHz, `0,013 × 3 000 000 000 = 39 000 000` cycles de temps écoulé. Ce n'est pas
encore une mesure de cycles CPU.

## 4. Prédictions formulées avant la mesure

Le mode de travail ne requiert plus une réponse préalable de l'apprenant. Les
hypothèses restent écrites avant l'exécution afin de ne pas les reconstruire à
partir des résultats :

1. deux lectures consécutives coûteront probablement des dizaines de ns sur cet
   environnement, avec une dispersion et de rares valeurs nettement plus grandes ;
2. une attente demandée de 100 ms prendra au moins environ 100 ms de temps écoulé,
   mais beaucoup moins de temps CPU ;
3. une charge active visant 50 ms de temps CPU aura des temps CPU et écoulé
   proches en l'absence de préemption prolongée ;
4. les répétitions ne seront pas identiques, notamment à cause de
   l'ordonnancement, des interruptions, de la fréquence et de la charge concurrente.

Ces prédictions sont qualitatives. Elles ne fixent pas une « bonne » durée
universelle.

## 5. Code et commandes

Le programme [`src/time_lab.c`](src/time_lab.c) lit les résolutions annoncées,
chronomètre deux lectures consécutives, amortit les lectures dans un lot, puis
compare une attente à une charge CPU active. `analyze.py` conserve les données
individuelles, calcule un résumé et produit une figure en quatre panneaux,
selon les [règles de style des figures](../../STYLE_FIGURES.md) :

- (a) ECDF du corps de la distribution des lectures, axe linéaire en ns ;
- (b) fonction de survie P(X ≥ x) en log-log, qui montre la traîne jusqu'au
  maximum ;
- (c) chaque répétition comme un point (temps CPU, temps écoulé), avec la
  diagonale écoulé = CPU ;
- (d) ECDF du dépassement de la durée demandée, en µs.

Les CSV produits avant l'ajout des colonnes `sleep_target_ns` et
`busy_target_ns` exigent les options `--sleep-target-ms` et `--busy-target-ms`.

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

## 6. Vérification indépendante de la performance

`make check` vérifie que l'attente retourne sans erreur et que son temps écoulé
observé atteint au moins la durée demandée. Ce test porte sur des propriétés de
correction et n'impose aucune limite supérieure de performance. Le compilateur a
également accepté le code avec les avertissements usuels activés.

## 7. Protocole de la première campagne

- Compilation C17 avec GCC, `-O2` et les options consignées ci-dessus.
- Graine fixe : `20260916` ; l'ordre attente/calcul alterne à chaque répétition.
- 50 000 paires de lectures consécutives de `CLOCK_MONOTONIC`.
- 50 répétitions de lots de 10 000 lectures pour amortir les bornes de mesure.
- 50 attentes demandées de 100 ms et 50 charges visant 50 ms de temps CPU.
- Temps écoulé : `CLOCK_MONOTONIC`; temps CPU :
  `CLOCK_PROCESS_CPUTIME_ID`.
- La préparation et l'écriture CSV sont hors des intervalles chronométrés.
- Pour l'attente et la charge, les quatre lectures d'horloge encadrantes sont
  incluses. La charge active interroge volontairement l'horloge CPU pendant son
  exécution : ce n'est pas un benchmark de calcul.
- Aucun cœur n'est fixé et aucun réglage système ou cache n'est modifié.
- Min, médiane, moyenne, p95 et max sont rapportés. Toutes les observations,
  y compris les valeurs atypiques, sont conservées.

Les versions, la topologie visible et le contexte d'exécution sont dans
[`data/environment-campaign.txt`](data/environment-campaign.txt). Les paramètres
sont aussi répétés dans chaque ligne du CSV.

## 8. Données et figures

- Données brutes : [`data/campaign.csv`](data/campaign.csv)
- Résumé calculé : [`reports/campaign-summary.csv`](reports/campaign-summary.csv)
- Figure matricielle 600 dpi : [`figures/campaign.png`](figures/campaign.png)
- Figure vectorielle : [`figures/campaign.pdf`](figures/campaign.pdf)
- Fiche superviseur : [`reports/supervisor-note.md`](reports/supervisor-note.md)

## 9. Résultats effectivement observés

Sur **cette campagne uniquement** :

| Variante et métrique | n | minimum | médiane | p95 | maximum |
|---|---:|---:|---:|---:|---:|
| Lectures consécutives, écoulé | 50 000 | 24 ns | 28 ns | 41 ns | 8 244 ns |
| Lecture en lot, coût par lecture | 50 | 27 ns | 27 ns | 27 ns | 28 ns |
| Charge active, écoulé | 50 | 50,001 ms | 50,003 ms | 50,096 ms | 50,249 ms |
| Charge active, CPU | 50 | 50,001 ms | 50,002 ms | 50,003 ms | 50,004 ms |
| Attente, écoulé | 50 | 100,054 ms | 100,086 ms | 100,146 ms | 100,215 ms |
| Attente, CPU | 50 | 0,018 ms | 0,027 ms | 0,037 ms | 0,039 ms |

`clock_getres` a annoncé une résolution de 1 ns pour les deux horloges. C'est une
propriété annoncée par l'API sur ce système, pas la preuve d'une exactitude à 1 ns.
Le panneau (a) rogne l'axe à 50 ns pour montrer le corps de la distribution et
annonce les 16 valeurs situées au-delà. Le panneau (b) les montre toutes : ses
deux axes logarithmiques multiplient les valeurs d'un même facteur entre deux
espacements égaux, ce qui rend visibles à la fois les dizaines de ns et la valeur
atypique en µs, sans retirer cette dernière.

## 10. Interprétation

L'attente fait progresser le temps écoulé d'environ 100 ms tout en consommant ici
quelques dizaines de µs de CPU : temps écoulé et temps CPU répondent donc bien à
deux questions différentes. Pour la charge active, les deux durées sont proches,
avec quelques surplus de temps écoulé compatibles avec des interruptions ou une
désélection par l'ordonnanceur.

La paire de lectures présente une valeur maximale de 8,244 µs, conservée dans les
données. Le lot donne une estimation bien plus stable, ici 27–28 ns par lecture.
Cela illustre pourquoi mesurer une opération unique dont le coût est du même ordre
que le chronomètre est fragile.

Treize millisecondes représentent environ 460 000 fois la médiane de 28 ns obtenue
pour une lecture mise en lot. Cela permet d'écarter **la simple lecture de
`CLOCK_MONOTONIC`** comme explication suffisante des 13 ms dans cet environnement.
Cela n'écarte pas le démarrage d'un outil de mesure ni les autres termes du modèle.

## 11. Limites et contrôles suivants

Cette expérience ne mesure ni TCP, ni HTTP, ni le programme original. Elle ne peut
donc pas attribuer les 13 ms au réseau, au framework, au client ou au serveur. Le
processus n'était pas fixé à un cœur, la machine n'était pas isolée et les données
ne proviennent que d'une campagne. Le p95 décrit ces 50 observations ; un p99 sur
un tel échantillon serait peu informatif.

Les prochains contrôles seront : répéter la campagne comme exécution indépendante,
tester l'affinité avec `taskset`, puis instrumenter séparément client et serveur du
cas localhost. `perf` sera essayé, mais la politique `perf_event_paranoid=4` peut
interdire les compteurs matériels.

## 12. Compréhension et prolongement

Questions facultatives : pourquoi une résolution annoncée de 1 ns n'implique-t-elle
pas une mesure exacte à 1 ns ? Pourquoi le temps CPU de l'attente n'est-il pas
strictement nul ? Que montre la valeur atypique de 8,244 µs, et que ne montre-t-elle
pas ?

Prolongement : ajouter des attentes de 1, 10 et 1 000 ms et tracer le dépassement
`durée observée − durée demandée`, sans supposer qu'il sera constant.
