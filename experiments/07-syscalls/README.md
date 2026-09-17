# D1 - Appels système : coût d'entrée dans le noyau et traitement par lots

## 1. Question et prérequis

**Question :** que coûte un passage de l'espace utilisateur au noyau, et que
gagne-t-on à regrouper le travail en lots, par un tampon de la bibliothèque C ou à
la main ? Quelle part du coût est fixe par appel, et quelle part dépend du nombre
d'octets traités ?

Prérequis : [A1](../01-time/README.md) (horloges, vDSO) et
[A2](../02-microbenchmark/README.md) (protocole de mesure : processus indépendants,
ordre aléatoire, contrôles A/A et positif). Les défauts de page de
[C2](../06-dependent-access/README.md) sont un cas particulier d'entrée dans le
noyau.

## 2. Notions nécessaires

Intuition : le noyau est un guichet. Poser une question au guichet coûte le trajet
et la file d'attente, même si la réponse est immédiate ; mieux vaut donc apporter
toutes ses questions en une fois.

- **Espace utilisateur, espace noyau** (*user space*, *kernel space*) : le programme
  s'exécute avec des droits restreints ; le noyau, avec tous les droits, gère le
  matériel, les fichiers et la mémoire.
- **Appel système** (*system call*, *syscall*) : demande explicite d'un service au
  noyau. Le processeur change de mode, le noyau vérifie les arguments, fait le
  travail, puis revient en mode utilisateur.
- **Atténuations** (*mitigations*) : protections contre les attaques par exécution
  spéculative (Spectre et variantes) qui ajoutent du travail à certaines entrées ou
  sorties du noyau. Leur état est lu dans
  `/sys/devices/system/cpu/vulnerabilities/`.
- **vDSO** (*virtual dynamic shared object*) : code fourni par le noyau mais exécuté
  en espace utilisateur ; `clock_gettime` y lit l'heure **sans** appel système.
- **Descripteur de fichier** (*file descriptor*) : entier qui désigne un fichier
  ouvert. `/dev/null` accepte les écritures sans les conserver ; `/dev/zero` fournit
  autant d'octets nuls que demandé.
- **Traitement par lots** (*batching*) : faire en un appel ce qui aurait demandé
  plusieurs appels. **Tampon** (*buffer*) : zone où l'on accumule les données avant
  de les transmettre ; `fwrite` de la bibliothèque C en utilise un.
- **Temps utilisateur et temps système** (*user time*, *system time*) : temps CPU
  passé respectivement dans le programme et dans le noyau pour son compte.

Ce qui est **garanti** : le résultat de chaque appel et, compté par le noyau dans
`/proc/self/io`, le nombre d'appels `read` et `write` (vérifiés). Ce qui **dépend
de la machine** : le coût d'entrée dans le noyau, les atténuations actives, la
vitesse de copie mémoire. Temps utilisateur et système sont comptés au tick près
(`CONFIG_HZ=1000`, soit 1 ms), donc seulement pour des échantillons de plusieurs
millisecondes.

## 3. Montage expérimental

Un programme, [`src/syscalls.c`](src/syscalls.c), compilé par GCC `-O2`, exécuté
sur un cœur P (CPU 11), un cœur E (CPU 19) et un cœur LP-E (CPU 21).

**Partie 1, entrée dans le noyau** :

| Mesure | Appels par échantillon | Ce qui est exécuté |
|---|---:|---|
| `function_call` | 2^20 | appel d'une fonction C, sans noyau |
| `vdso_clock_gettime` | 2^20 | `clock_gettime` par le vDSO, sans noyau |
| `syscall_clock_gettime` | 2^18 | **le même travail** par un vrai appel système |
| `syscall_getppid` | 2^18 | appel système minimal qui rend un entier |
| `syscall_getppid_bis` | 2^18 | contrôle A/A |
| `syscall_getppid_double` | 2^18 itérations, 2 appels chacune | contrôle positif (coût attendu × 2) |
| `syscall_enosys` | 2^18 | numéro d'appel inexistant : entrée, refus, sortie |

**Partie 2, lots** : `write` sur `/dev/null` (le noyau ne copie rien) et `read` sur
`/dev/zero` (le noyau copie des zéros dans le tampon du programme), par blocs de
1, 4, 16... 1 048 576 octets : 2^16 appels par échantillon jusqu'à 4 Kio, puis
256 Mio au total.

**Partie 3, tampon utilisateur** : enregistrements de 16 octets écrits sur
`/dev/null` :

| Mesure | Enregistrements | Appels `write` attendus |
|---|---:|---|
| `records_write_each` | 2^18 | un par enregistrement |
| `records_stdio_default` | 2^20 | un par tampon de `fwrite` (4 Kio choisis par la bibliothèque C pour `/dev/null`) |
| `records_stdio_64k` | 2^20 | un par tampon de 64 Kio (`setvbuf`) |
| `records_manual_4k` | 2^20 | un par tampon de 4 Kio rempli à la main |

Autour de chaque échantillon, hors chronométrage : CPU, temps utilisateur et
système (`getrusage`), appels `read` et `write` comptés par le noyau
(`/proc/self/io`).

## 4. Prédictions, écrites avant la campagne

**Transparence :** un essai de mise au point (cœur P, 2 tours) a servi à mesurer la
durée totale d'un tour (0,5 s) et à vérifier les **nombres** d'appels système ; les
durées par mesure n'ont pas été examinées.

Cœur P, entrée dans le noyau :

1. `function_call` : 1 à 3 ns ; `vdso_clock_gettime` : 15 à 40 ns (A1 : 28 ns pour
   deux lectures consécutives) ; `syscall_clock_gettime` : 60 à 300 ns, soit **3 à
   15 fois le même travail par le vDSO**.
2. `syscall_getppid` : 50 à 250 ns ; `syscall_enosys` entre 0,6 et 1,0 fois
   `syscall_getppid`.
3. Contrôles : `syscall_getppid_bis / syscall_getppid` entre 0,97 et 1,03 par
   processus ; `syscall_getppid_double / syscall_getppid` entre 1,8 et 2,2.
4. Cœurs : pour les appels système, E / P entre 1,2 et 2,5 et LP-E / P entre 1,3 et 3.

Lots (cœur P), avec le modèle fixé à l'avance `coût d'un appel = S + b × bloc`,
ajusté par moindres carrés relatifs sur les médianes :

5. `/dev/null` : coût par appel indépendant de la taille du bloc à 30 % près de
   1 octet à 1 Mio ; `b` inférieur à 0,001 ns par octet.
6. `/dev/zero` : coût par appel à peu près constant jusqu'à 1 à 4 Kio, puis
   proportionnel au bloc ; `S` entre 1 et 2 fois le coût d'une écriture sur
   `/dev/null` d'un octet ; `b` entre 0,03 et 0,2 ns par octet (copie de 5 à
   30 Gio/s) ; taille de bloc où coût fixe et coût par octet s'égalent (`S / b`)
   entre 1 et 16 Kio.

Tampon utilisateur (cœur P) :

7. `records_write_each` : coût par enregistrement à 30 % près d'une écriture de
   16 octets sur `/dev/null` ; `records_stdio_default` : 5 à 25 ns par
   enregistrement, **au moins 10 fois moins** ; `records_stdio_64k` entre 0,5 et
   1,0 fois `records_stdio_default` ; `records_manual_4k` entre 0,3 et 1,0 fois
   `records_stdio_default`.
8. Nombre d'appels `write` exactement : un par enregistrement, 4 096 pour les
   tampons de 4 Kio, 256 pour le tampon de 64 Kio (vérifié par `verify.py`, donc
   condition de validité plutôt que prédiction).
9. Part du temps système, `système / (utilisateur + système)` : au moins 0,7 pour
   `syscall_getppid`, `syscall_enosys`, `records_write_each` et les écritures sur
   `/dev/null` de blocs de 16 octets ou moins ; au plus 0,05 pour `function_call`
   et `vdso_clock_gettime` ; au plus 0,2 pour `records_stdio_64k`.

## 5. Code et commandes

- [`src/syscalls.c`](src/syscalls.c) : mesures, plan construit avant la première
  mesure, comptes du noyau et `getrusage` autour de chaque échantillon,
  vérification de chaque résultat.
- [`prepare.py`](prepare.py), [`run.sh`](run.sh) : plan des processus mélangé,
  épinglage.
- [`verify.py`](verify.py) : complétude, épinglage, exactitude recalculée en
  Python, nombres d'appels système comparés aux comptes du noyau.
- [`analyze.py`](analyze.py) : résumés, ajustements et figures selon
  [`STYLE_FIGURES.md`](../../STYLE_FIGURES.md).

```sh
make check      # correction et nombres d'appels système
make quick      # validation de la chaîne
make campaign   # campagne documentée ; refuse d'écraser data/campaign
make analyze    # résumés et figures depuis data/campaign
```

## 6. Vérification de correction, indépendante de la mesure

- `--self-test` : chaque mesure sur quelques appels, avec résultats attendus et
  nombre minimal d'appels `read` et `write` comptés par le noyau.
- Pendant la campagne, hors chronométrage : chaque résultat comparé à sa valeur
  attendue ; dernier bloc lu sur `/dev/zero` vérifié nul.
- `verify.py` : valeurs attendues recalculées en Python ; pour **chaque**
  échantillon, nombres d'appels `read` et `write` comptés par le noyau égaux aux
  nombres attendus, après retrait du décalage constant (2 lectures) dû à la
  lecture de `/proc/self/io` elle-même.
- La taille du tampon choisie par la bibliothèque C est lue sur le flux (champ
  interne de la glibc) et enregistrée.

## 7. Protocole de la campagne

- 3 types de cœurs × 10 processus indépendants = 30 processus, ordre aléatoire fixé
  (graine `20260920`), épinglés sur le CPU 11, 19 ou 21.
- 11 tours par processus, le premier déclaré échauffement ; dans chaque tour, les
  33 mesures dans un ordre tiré au hasard.
- Unité statistique : le processus ; médiane sur 10 tours du coût par appel (ou par
  enregistrement). Entre processus : médiane et intervalle bootstrap percentile
  à 95 %.
- Rapports (prédictions 1 à 4, 7) : par processus, puis résumés.
- Modèle `S + b × bloc` : moindres carrés relatifs sur les médianes entre
  processus des 11 tailles de bloc, par cœur et par fichier spécial.
- Part du temps système : sommes des temps utilisateur et système des 10 tours
  mesurés, par processus (mesure jugée invalide après coup, voir 10.4).
- Aucun réglage global de la machine.

## 8. Données brutes

- [`data/campaign/`](data/campaign/) : `plan.csv` (écrit avant la mesure),
  `topology.csv`, un fichier `run-NNN.csv` par processus (une ligne par
  échantillon : mesure, taille de bloc, nombre d'appels, durée, temps utilisateur et
  système, appels `read` et `write` comptés par le noyau, CPU, résultat, valeur
  attendue) et `run-NNN-meta.csv` (taille du tampon de `fwrite`, changements de
  contexte).
- [`data/environment-campaign.txt`](data/environment-campaign.txt) : machine,
  atténuations actives, options du noyau (`CONFIG_HZ`, comptabilité du temps CPU),
  version de la glibc, empreintes SHA-256.
- Résumés : `reports/campaign-costs.csv` (coût par appel et part du temps système,
  par cœur et mesure), `-ratios.csv`, `-model.csv` (`S`, `b` et taille de
  croisement), `-meta.csv`.

Les 10 890 échantillons (30 processus × 11 tours × 33 mesures) ont un résultat
exact, et pour chacun les nombres d'appels `read` et `write` comptés par le noyau
sont exactement ceux attendus. Aucune observation retirée.

## 9. Figures

- [`figures/campaign-entry.pdf`](figures/campaign-entry.pdf) : coût par appel pour
  entrer dans le noyau (a) et coût par enregistrement selon la façon d'écrire (b),
  un point par processus, sur les cœurs P, E et LP-E.
- [`figures/campaign-batching.pdf`](figures/campaign-batching.pdf) : coût par appel
  selon la taille du bloc pour `write` sur `/dev/null` (a) et `read` sur
  `/dev/zero` (b), avec le modèle `S + b × bloc` ajusté ; coût par octet (c).

La part du temps système, prévue à l'origine comme panneau de la seconde figure,
n'est pas tracée : section 10.4.

## 10. Résultats observés et interprétation

Médianes entre 10 processus par cœur.

### 10.1 Entrer dans le noyau coûte environ 110 ns

| Coût par appel (ns) | Cœur P | Cœur E | Cœur LP-E |
|---|---:|---:|---:|
| Appel de fonction | 0,60 | 1,51 | 1,23 |
| `clock_gettime` par le vDSO | 21,6 | 33,3 | 29,4 |
| `clock_gettime` par appel système | 159,5 | 248,1 | 220,5 |
| Appel inexistant (`ENOSYS`) | 108,9 | 156,7 | 134,5 |
| `getppid` | 116,5 | 165,8 | 140,5 |

- **Le même travail coûte 7,4 fois plus par un appel système que par le vDSO**,
  sur les trois cœurs (7,40 ; 7,42 ; 7,41). Prédiction 1 confirmée pour ce rapport
  (3 à 15), pour le vDSO (15 à 40 ns) et l'appel système (60 à 300 ns) ; réfutée
  pour l'appel de fonction, plus rapide que prévu (0,60 ns au lieu de 1 à 3).
- **Un appel inexistant coûte 93 % de `getppid`** : l'entrée dans le noyau et la
  sortie font presque tout le coût d'un appel système simple. Prédiction 2
  confirmée (116,5 ns ; rapport 0,93).
- Un appel système minimal coûte environ **190 appels de fonction** sur le cœur P,
  110 sur les cœurs E et LP-E.
- Cœurs : `getppid` coûte 1,42 fois plus sur le cœur E et 1,21 fois plus sur le
  cœur LP-E que sur le cœur P. Prédiction 4 confirmée pour E, réfutée de peu pour
  LP-E (borne basse 1,3). Le cœur LP-E est plus rapide que le cœur E pour tous les
  appels système mesurés, sans explication établie.
- Contrôles : `getppid` A/A de 0,974 à 1,031 (P), 0,989 à 1,027 (E), 0,966 à 1,041
  (LP-E) ; contrôle positif de 1,94 à 2,11. Prédiction 3 confirmée pour le contrôle
  positif ; l'A/A sort de quelques millièmes de l'intervalle 0,97 à 1,03 sur les
  cœurs P et LP-E.

### 10.2 Lots : un coût fixe par appel, un coût par octet seulement s'il y a copie

| Modèle `S + b × bloc` | `S` (ns par appel) | `b` (ns par octet) | Croisement `S / b` | Débit à 1 Mio |
|---|---:|---:|---:|---:|
| P, `write` sur `/dev/null` | 157 | 0 (≈ -0,000002) | sans objet | 6 276 Gio/s |
| P, `read` sur `/dev/zero` | 173 | 0,022 | 7,7 Kio | 33,6 Gio/s |
| E, `read` sur `/dev/zero` | 272 | 0,044 | 6,0 Kio | 20,3 Gio/s |
| LP-E, `read` sur `/dev/zero` | 233 | 0,037 | 6,1 Kio | 23,7 Gio/s |

- **`/dev/null` ne dépend pas de la taille du bloc** : 157 ns par appel pour
  1 octet comme pour 1 Mio sur le cœur P (rapport 1,01). Écrire 1 Mio d'un coup ou
  1 octet coûte la même chose ; écrire 1 Mio octet par octet coûte 1 million de
  fois plus. Prédiction 5 confirmée.
- **`/dev/zero` copie** : coût quasi constant jusqu'à 1 Kio, puis proportionnel à la
  taille. Au-delà d'environ 6 à 8 Kio par appel, copier coûte plus que d'entrer dans
  le noyau. Prédiction 6 confirmée pour `S` (1,10 fois l'écriture sur `/dev/null`)
  et pour le croisement (1 à 16 Kio) ; `b` = 0,022 ns par octet sur le cœur P est
  **juste sous** la borne basse de 0,03 (copie à 34 Gio/s au lieu d'au plus 30).
- Le coût par octet (c) montre les deux régimes : pour de petits blocs, il décroît
  comme `1 / bloc`, le coût fixe domine ; pour de grands blocs, il se stabilise au
  coût de la copie.

### 10.3 Tampon utilisateur : le tampon supprime les appels système, pas le coût de `fwrite`

| Écrire un enregistrement de 16 octets | Cœur P | Cœur E | Cœur LP-E | Appels `write` pour 2^20 enregistrements |
|---|---:|---:|---:|---:|
| `write` par enregistrement | 157,7 ns | 232,1 ns | 199,5 ns | 1 048 576 |
| `fwrite`, tampon de 4 Kio | 12,8 ns | 20,6 ns | 17,4 ns | 4 096 |
| `fwrite`, tampon de 64 Kio | 12,5 ns | 19,7 ns | 16,7 ns | 256 |
| Tampon manuel de 4 Kio | 1,7 ns | 2,5 ns | 2,1 ns | 4 096 |

- `write` par enregistrement coûte exactement une écriture de 16 octets sur
  `/dev/null` (rapport 1,000) ; `fwrite` est **12,3 fois** plus rapide. Prédiction 7
  confirmée pour ces deux points et pour le tampon de 64 Kio (0,97 fois le tampon de
  4 Kio).
- **Prédiction 7 réfutée pour le tampon manuel** : il coûte 0,13 fois `fwrite`
  (prédit 0,3 à 1,0). Avec 4 096 appels à 157 ns pour 1 048 576 enregistrements, les
  appels système ne pèsent que 0,6 ns par enregistrement. Le reste des 12,8 ns de
  `fwrite` vient de l'appel lui-même ; hypothèse : le verrou que la glibc prend sur
  le flux à chaque appel, et la copie dans son tampon (à tester avec
  `fwrite_unlocked`).
- Le tampon de 64 Kio ne gagne que 3 % : les appels système n'étaient déjà plus le
  coût dominant.
- Prédiction 8 : nombres d'appels `write` exactement conformes (condition vérifiée
  pour chaque échantillon).

### 10.4 Temps utilisateur et temps système : mesure invalide

La part `système / (utilisateur + système)` vaut 0,25 pour un simple appel de
fonction, qui n'entre jamais dans le noyau, et seulement 0,48 à 0,67 pour les appels
système. **Prédiction 9 non testable.** D'après le code du noyau
(`kernel/sched/cputime.c`, fonction `cputime_adjust`), `getrusage` rend le temps
d'exécution exact du processus, **réparti** entre utilisateur et système selon la
proportion des ticks relevés en mode utilisateur ou noyau **depuis le début du
processus** (sans `nohz_full`, la comptabilité reste échantillonnée au tick, même
avec `CONFIG_VIRT_CPU_ACCOUNTING_GEN`). La différence entre deux lectures, sur une
fenêtre de quelques millisecondes, hérite donc de toute l'histoire du processus.
Les valeurs restent dans `reports/campaign-costs.csv`, mais ne sont ni tracées ni
interprétées.

### 10.5 Ce que D1 permet et ne permet pas de conclure

Permet de conclure, sur cette machine :

- un appel système simple coûte 110 à 165 ns selon le cœur, dont plus de 90 % pour
  entrer dans le noyau et en sortir ;
- lire l'heure par le vDSO évite 86 % de ce coût ;
- regrouper les écritures divise le coût par le nombre d'éléments regroupés tant
  que le coût fixe domine, soit jusqu'à environ 6 à 8 Kio par appel quand le noyau
  copie les données ;
- un tampon de bibliothèque supprime presque tous les appels système, mais l'appel
  de bibliothèque peut devenir le coût dominant.

Ne permet pas de conclure :

- la répartition entre temps utilisateur et temps système à l'échelle de la
  milliseconde (mesure invalide, 10.4) ;
- le coût d'appels système qui attendent (réseau, disque) : ici, aucun ne bloque ;
- la part des atténuations Spectre dans le coût d'entrée : elles ne peuvent pas
  être désactivées sans réglage global.

Pour les 13 ms : à 116 ns par appel, il en faudrait environ 110 000 appels système
**non bloquants** pour les atteindre. Une requête localhost en fait quelques
dizaines à quelques centaines : les appels système eux-mêmes sont une explication
peu plausible, **sauf s'ils attendent** (connexion, lecture réseau, écriture de
journaux avec `fsync`). C'est ce que J1 et D2 examineront.

## 11. Limites et expériences suivantes

- Un CPU par type de cœur, une campagne de 3,5 minutes ; charge moyenne de 1,16 au
  départ.
- Fichiers spéciaux uniquement : ni cache de pages, ni stockage, ni réseau.
- Atténuations et options du noyau fixées ; leur effet n'est pas séparé.
- Taille du tampon de `fwrite` lue dans une structure interne de la glibc.

Expériences suivantes :

1. **D2, fichiers et persistance** : écriture mise en tampon par le noyau contre
   `fsync`, lecture servie par le cache de pages contre accès au stockage, sans vider
   les caches système (réglage global soumis à votre accord).
2. Tester l'hypothèse du verrou de `fwrite` : mêmes mesures avec
   `fwrite_unlocked` et `putc_unlocked`.
3. Mesurer le temps système par un moyen fiable : `CLOCK_THREAD_CPUTIME_ID` ne
   sépare pas les modes ; il faudrait `perf stat` (accord requis) ou un noyau avec
   comptabilité précise par tâche.

## 12. Compréhension et prolongement

Questions :

1. Pourquoi un appel système inexistant coûte-t-il presque autant que `getppid`, et
   qu'en déduire sur ce que coûte un appel système simple ?
2. Pourquoi `clock_gettime` coûte-t-il 7 fois moins par le vDSO, et quelles
   informations le vDSO peut-il fournir sans entrer dans le noyau ?
3. Pourquoi la taille du bloc ne change-t-elle rien pour `/dev/null`, mais tout pour
   `/dev/zero` au-delà de quelques Kio ?
4. Le tampon de `fwrite` réduit les appels système par 256, mais un tampon manuel
   reste 7 fois plus rapide. Qu'est-ce que cela apprend sur la façon de chercher le
   coût dominant ?
5. Pourquoi la différence entre deux appels à `getrusage` ne mesure-t-elle pas le
   temps système d'une fenêtre de quelques millisecondes ?

Prolongement : mesurer l'écriture des mêmes enregistrements avec `writev`, en
regroupant 16, 64, 256 et 1 024 enregistrements par appel. Prédire, avant de
mesurer, le coût par enregistrement à partir de `S` et de la mesure du tampon
manuel, puis comparer.
