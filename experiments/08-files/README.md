# D2 - Fichiers et persistance : cache de pages, stockage et fsync

## 1. Question et prérequis

**Question :** que coûte une lecture servie par le cache de pages, comparée à une
lecture qui doit attendre le stockage ? Et que coûte une écriture simplement confiée
au noyau, comparée à une écriture dont on demande la persistance (`fsync`,
`fdatasync`, `O_DSYNC`) ? Que rapporte le regroupement des demandes de persistance ?

Prérequis : [D1](../07-syscalls/README.md) (coût d'un appel système, tampons,
traitement par lots) et [A2](../02-microbenchmark/README.md) (protocole : processus
indépendants, ordre aléatoire, contrôles A/A et positif). Les défauts de page de
[C2](../06-dependent-access/README.md) sont un autre usage des pages du noyau.

## 2. Notions nécessaires

**Intuition.** Le noyau garde une copie en mémoire des fichiers récemment utilisés.
Lire un fichier déjà copié revient à lire la mémoire ; sinon, il faut attendre le
disque. À l'écriture, le noyau prend les données, rend la main tout de suite, et ne
les écrit sur le disque que plus tard, sauf si on lui demande d'attendre.

- **Cache de pages** (*page cache*) : pages de mémoire où le noyau garde le contenu
  des fichiers. Une lecture qui y trouve ses données ne touche pas le disque.
- **Lecture à chaud, à froid** (*warm*, *cold read*) : ici, toutes les pages du fichier
  sont dans le cache (chaud), ou aucune (froid).
- **Lecture anticipée** (*readahead*) : quand les lectures sont séquentielles, le noyau
  lit plus loin que demandé, en avance.
- **`O_DIRECT`** (*direct I/O*) : lecture ou écriture qui contourne le cache de pages
  et va directement au périphérique.
- **Page sale** (*dirty page*) : page du cache modifiée mais pas encore écrite sur le
  disque. Le noyau l'écrit plus tard (*writeback*), par défaut au plus 30 s après.
- **`fsync`, `fdatasync`** : attendent que les données d'un fichier soient écrites et
  que le disque confirme. `fsync` attend aussi les métadonnées (taille, dates) ;
  `fdatasync` seulement celles nécessaires pour relire les données (la taille, pas les
  dates). **`O_DSYNC`** : chaque `write` se comporte comme `write` puis `fdatasync`.
- **Journal** (*journal*, *jbd2*) : ext4 écrit d'abord les modifications de
  métadonnées dans un journal, par **transactions** validées (*commit*) ensemble.
- **Vidage du cache du disque** (*flush*) et **FUA** (*force unit access*) : le disque
  garde lui aussi les écritures dans une mémoire volatile ; une requête *flush* lui
  demande de les rendre persistantes, et le drapeau FUA le demande pour une seule
  écriture.
- **Folio** (*folio*) : unité de gestion du cache de pages, d'une page de 4 Kio ou de
  plusieurs pages contiguës (grand folio).
- **Fonction de répartition empirique** (*ECDF*) : pour chaque durée, la fraction des
  opérations qui ont duré au plus autant.

### Notations

**Lectures** d'un fichier de 256 Mio au contenu pseudo-aléatoire vérifiable :

| Mesure (nom dans les données) | Opérations par échantillon | Ce qui est exécuté |
|---|---:|---|
| `seq_read_warm` | 2 048 `read` de 128 Kio | tout le fichier, déjà en cache |
| `seq_read_cold` | 2 048 `read` de 128 Kio | tout le fichier, retiré du cache juste avant |
| `seq_read_direct` | 2 048 `read` de 128 Kio | tout le fichier, en `O_DIRECT` |
| `rand_read_warm` | 256 `pread` de 4 Kio | pages distinctes tirées au hasard, en cache |
| `rand_read_cold` | 256 `pread` de 4 Kio | idem, fichier retiré du cache, lecture anticipée désactivée (`POSIX_FADV_RANDOM`) |
| `rand_read_cold_bis` | 256 `pread` de 4 Kio | identique : contrôle A/A, rapport vrai 1 |
| `rand_read_direct` | 256 `pread` de 4 Kio | en `O_DIRECT` |
| `rand_read_direct_double` | 256 opérations de 2 `pread` | contrôle positif : coût attendu × 2 |

**Écritures** d'enregistrements de 4 Kio, 256 par échantillon, un fichier par mesure.
« Ajout » : le fichier est vidé avant l'échantillon et grandit à chaque écriture.
« Réécriture » : les 256 blocs existent déjà et sont remplacés.

| Mesure | Opération chronométrée | Fichier |
|---|---|---|
| `append_buffered` | `pwrite` seul ; un `fsync` final est chronométré à part | ajout, ext4 |
| `append_fsync`, lot de $k$ = 1, 4, 16, 64, 256 | $k$ `pwrite` puis un `fsync` | ajout, ext4 |
| `append_fdatasync` | `pwrite` puis `fdatasync` | ajout, ext4 |
| `tmpfs_append_fsync` | `pwrite` puis `fsync` | ajout, tmpfs : témoin sans disque |
| `overwrite_fsync` | `pwrite` puis `fsync` | réécriture, blocs initialisés page par page |
| `overwrite_fdatasync` | `pwrite` puis `fdatasync` | idem |
| `overwrite_fdatasync_bis` | idem | contrôle A/A |
| `overwrite_fdatasync_double` | 2 × (`pwrite` puis `fdatasync`) | contrôle positif : coût attendu × 2 |
| `overwrite_odsync` | `pwrite` sur un fichier ouvert avec `O_DSYNC` | réécriture, blocs initialisés page par page |
| `overwrite_fdatasync_folio` | comme `overwrite_fdatasync` | réécriture, 256 blocs initialisés en une seule écriture (grand folio) |
| `overwrite_odsync_folio` | comme `overwrite_odsync` | idem |

**Symboles :**

| Symbole | Signification | Unité |
|---|---|---|
| $t$ | latence d'une opération (lecture, écriture, ou lot suivi de sa demande de persistance) | µs, ms |
| $\tilde t$ | médiane des latences d'une mesure dans un processus, sur ses 10 tours mesurés | µs, ms |
| $t_{99}$ | 99ᵉ centile de ces latences | µs, ms |
| $D$ | débit d'une lecture séquentielle : 256 Mio divisés par la durée de l'échantillon ; médiane des tours | Gio/s |
| $k$ | nombre d'enregistrements par demande de persistance (taille du lot) | |
| $F$ | coût fixe d'un lot suivi de `fsync` | ms |
| $w$ | coût supplémentaire par enregistrement du lot | µs |
| $t_{\text{diff}}$ | durée du `fsync` final de `append_buffered` (persistance différée) | ms |
| $v$, $j$ | vidages du disque et transactions du journal par opération (médiane sur les échantillons) | |

Les rapports s'écrivent avec le nom abrégé de la mesure en indice, par exemple
$\tilde t_{\text{cold}}/\tilde t_{\text{warm}}$ pour `rand_read_cold` sur
`rand_read_warm`, et se calculent par processus.

Ce qui est **garanti** : le contenu de chaque bloc lu et de chaque enregistrement relu
(vérifié), l'état du cache de nos fichiers avant chaque lecture (`mincore`), et les
appels et octets comptés par le noyau pour le processus. Ce qui **dépend de la
machine** : le disque et son micrologiciel, le système de fichiers et ses options, les
états de veille du processeur et du disque. Ce qui **ne peut pas être vérifié ici** :
la persistance elle-même, qui exigerait de couper l'alimentation.

## 3. Modèle de coût et prédictions, écrits avant la campagne

**Transparence.** Pendant la mise au point, deux essais ont été examinés :

- Un essai de contrôle (fichier de 8 Mio, 2 tours) : j'ai examiné les **comptes**
  (appels, octets, pages en cache, requêtes du disque, transactions du journal,
  changements de contexte), **pas les durées**. Il a montré : un vidage du disque et
  une transaction du journal par `fsync` ; un vidage sans transaction par `fdatasync`
  en réécriture ; une transaction par `fdatasync` en fin de fichier ; 8 secteurs
  (4 Kio) écrits sur le disque par réécriture, mais 1 Mio compté dans `write_bytes`
  quand le fichier avait été écrit d'un seul bloc de 1 Mio ; et, au premier essai
  seulement, **0 ou 1 vidage** pour 256 écritures `O_DSYNC` (256 dans les essais
  suivants, après modification de l'initialisation). Ces constats ont motivé les
  variantes `_folio` et l'ajout des secteurs écrits. Ils ne sont donc **pas** des
  prédictions : ce sont des faits de mécanisme à confirmer par la campagne.
- Un essai de durée (fichier de 256 Mio, 2 tours) : seule la durée totale a été lue
  (23 s).

**Modèle des lots**, fixé à l'avance. Un lot de $k$ enregistrements suivi d'un `fsync`
coûte un coût fixe plus un coût par enregistrement, d'où le coût par enregistrement :

$$
t(k) = F + w\,k,
\qquad
\frac{t(k)}{k} = w + \frac{F}{k},
$$

ajusté par moindres carrés relatifs sur les médianes entre processus des 5 tailles de
lot.

Toutes les prédictions portent sur le cœur P, en médiane par processus.

Lectures :

1. $\tilde t$ de `rand_read_warm` : 0,3 à 2 µs par lecture de 4 Kio.
2. $\tilde t$ de `rand_read_cold` : 50 à 300 µs, soit
   $\tilde t_{\text{cold}}/\tilde t_{\text{warm}} \geq 50$ ;
   $t_{99}/\tilde t$ entre 1,2 et 5.
3. $\tilde t_{\text{direct}}/\tilde t_{\text{cold}}$ entre 0,7 et 1,1.
4. Contrôles : $\tilde t_{\text{cold bis}}/\tilde t_{\text{cold}}$ entre 0,9 et 1,1 par
   processus ; $\tilde t_{\text{direct double}}/\tilde t_{\text{direct}}$ entre 1,8 et
   2,2.
5. Débit séquentiel : $D$ de `seq_read_warm` de 5 à 30 Gio/s ; de `seq_read_cold` de
   0,5 à 4 Gio/s, avec $D_{\text{warm}}/D_{\text{cold}} \geq 3$ ;
   $D_{\text{direct}}/D_{\text{cold}}$ entre 0,5 et 1,5.

Écritures :

6. $\tilde t$ de `append_buffered` : 1 à 10 µs ; $t_{\text{diff}}$ (1 Mio) : 1 à 20 ms.
7. $\tilde t$ de `append_fsync` à $k = 1$ : 0,5 à 10 ms, **au moins 100 fois**
   `append_buffered` et au moins 100 fois `tmpfs_append_fsync`, lui-même de 1 à 5 µs.
8. $\tilde t_{\text{overwrite fdatasync}}/\tilde t_{\text{overwrite fsync}}$ entre 0,3
   et 0,9 (pas de transaction du journal) ;
   $\tilde t_{\text{append fdatasync}}/\tilde t_{\text{append fsync}}$ entre 0,8 et 1,25
   (la taille change, la transaction reste nécessaire).
9. $\tilde t_{\text{overwrite odsync}}/\tilde t_{\text{overwrite fdatasync}}$ entre 0,8
   et 1,25.
10. Variantes `_folio` : entre 0,8 et 1,25 fois leur équivalent initialisé page par
    page.
11. Contrôles : $\tilde t_{\text{fdatasync bis}}/\tilde t_{\text{fdatasync}}$ entre 0,9
    et 1,1 ; $\tilde t_{\text{fdatasync double}}/\tilde t_{\text{fdatasync}}$ entre 1,8
    et 2,2.
12. Lots : $t(256)/256 \leq t(1)/20$ ; $F$ entre 0,7 et 1,3 fois $t(1)$ ; $w$ entre 1
    et 20 µs.
13. `append_buffered` suivi de son `fsync` final, ramené à l'enregistrement, entre 0,8
    et 1,25 fois $t(256)/256$ (même travail, chronométré en deux fois).

## 4. Code et parties importantes

- [`src/files.c`](src/files.c), compilé par GCC `-O2` : création du fichier lu, plan
  des mesures construit avant la première mesure, préparation de l'état du cache,
  chronométrage par opération, relecture et vérification, compteurs du noyau.
- [`prepare.py`](prepare.py) : plan des processus, CPU choisi, périphérique et journal
  retrouvés à partir du système de fichiers de `build/scratch`.
- [`run.sh`](run.sh) : exécution épinglée ; interruptions du NVMe par CPU relevées
  avant et après.
- [`verify.py`](verify.py) : vérifications indépendantes (section 6).
- [`analyze.py`](analyze.py) : résumés, modèle et figures selon
  [`STYLE_FIGURES.md`](../../STYLE_FIGURES.md).

**Montage.** Le programme s'exécute sur le cœur P de plus grand numéro (CPU 11).
Stockage : ext4 (`data=ordered`, `delalloc`, `barrier`, `commit=5`) sur LVM, sur un
SSD NVMe Samsung `MZVL21T0HCLR` (1 To, cache d'écriture volatile annoncé, FUA
annoncé). Témoin : tmpfs (`/dev/shm`), sans disque.

**Aucun réglage global.** Les caches système ne sont pas vidés : seules les pages de
**notre** fichier sont retirées du cache par `posix_fadvise(POSIX_FADV_DONTNEED)`,
possible parce qu'elles sont propres, et le retrait est contrôlé par `mincore`.

Chaque opération est chronométrée seule ; les vérifications restent hors des fenêtres.
Autour de chaque échantillon, hors chronométrage, le programme relève : pages en cache
(`mincore`), appels `read`/`write` et octets lus ou écrits pour le processus
(`/proc/self/io`), changements de contexte ; et, pour toute la machine, requêtes de
lecture, d'écriture et de vidage du disque (`/sys/block/nvme0n1/stat`) et transactions
du journal ext4 (`/proc/fs/jbd2/dm-0-8/info`).

Les fichiers de travail sont dans `build/scratch/` (ignoré par Git) et
`/dev/shm/labs-d2-*` (retiré à la fin).

## 5. Commandes

```sh
make check      # auto-test, essai court et vérification
make quick      # validation de la chaîne (1 processus, 3 tours)
make campaign   # campagne documentée ; refuse d'écraser data/campaign
make analyze    # résumés et figures depuis data/campaign
make clean      # retire build/, dont le fichier lu de 256 Mio
```

## 6. Vérification de correction, indépendante de la mesure

- `--self-test` : fichier de 4 Mio, un tour de toutes les mesures ; contenu exact, cache
  vide avant une lecture à froid et plein avant une lecture à chaud.
- Pendant la mesure, hors chronométrage : somme de contrôle de chaque bloc lu comparée
  à la table calculée à la création ; chaque enregistrement écrit relu **sans le cache
  de pages** (`O_DIRECT`) sur ext4, et comparé ; taille du fichier contrôlée.
- `verify.py` : nombre d'unités exactes recalculé depuis le plan ; aucune page en cache
  avant une lecture à froid, toutes avant une lecture à chaud ; appels `read` et
  `write` exacts ; aucun octet lu du stockage pour une lecture à chaud, au moins les
  octets demandés pour une lecture à froid ou directe, aucun octet d'écriture compté
  sur tmpfs ; somme des latences par opération égale à la durée de l'échantillon ;
  66 blocs du fichier lu régénérés en Python et comparés octet à octet. Un essai de
  mutation (page en cache, octets lus, octet du fichier modifiés) a bien fait échouer
  chacune de ces vérifications.

## 7. Protocole de la campagne

- 10 processus indépendants, épinglés sur le CPU 11, lancés l'un après l'autre.
- 11 tours par processus, le premier déclaré échauffement ; dans chaque tour, les
  23 mesures dans un ordre tiré au hasard (graine `20260921`).
- Unité statistique : le processus. Lectures aléatoires et écritures : $\tilde t$ et
  $t_{99}$ sur les 10 tours mesurés (2 560 opérations au lot de 1). Lectures
  séquentielles : $D$, médiane sur les tours. Entre processus : médiane et IC 95 %
  bootstrap percentile (10 000 tirages).
- Rapports (prédictions 2 à 5, 7 à 11, 13) : par processus, puis résumés.
- Modèle $t(k) = F + w\,k$ : moindres carrés relatifs sur les médianes entre processus
  des 5 tailles de lot.
- Comptes de mécanisme par opération ($v$, $j$, secteurs écrits, changements de
  contexte volontaires) : médiane par mesure. D'autres processus peuvent y contribuer.
- Rien d'autre de lourd sur la machine pendant la campagne (environ 20 min) ; environ
  4 Gio écrits sur le SSD au total.

## 8. Données brutes

- [`data/campaign/`](data/campaign/) : `plan.csv` et `storage.csv` (écrits avant la
  mesure) ; par processus, `run-NNN.csv` (une ligne par échantillon : mesure, durée,
  $t_{\text{diff}}$, unités exactes, pages en cache avant et après, appels et octets du
  processus, requêtes, secteurs et vidages du disque, transactions du journal,
  changements de contexte, CPU), `run-NNN-ops.csv` (latence de chaque opération des
  lectures aléatoires et des écritures) et `run-NNN-meta.csv` ;
  `interrupts-before.txt` et `interrupts-after.txt` (interruptions du NVMe par CPU).
- [`data/environment-campaign.txt`](data/environment-campaign.txt) : machine, options
  d'ext4, files du disque (FUA, cache d'écriture, lecture anticipée), réglages de
  l'écriture différée, états de veille du CPU 11, empreintes SHA-256.
- Résumés : `reports/campaign-summary.csv` ($\tilde t$, $t_{99}$, $D$),
  `-ratios.csv`, `-model.csv`, `-mechanism.csv` (comptes par opération), `-meta.csv`.

La campagne a duré 20 min (charge moyenne de 0,63 au départ). Les 2 530 échantillons
(10 processus × 11 tours × 23 mesures) et leurs 459 910 opérations ont passé toutes
les vérifications ; aucun retrait du cache n'a dû être redemandé. Aucune observation
retirée.

## 9. Figures

- [`figures/campaign-reads.pdf`](figures/campaign-reads.pdf) : fonction de répartition
  empirique des latences des 25 600 lectures aléatoires de 4 Kio par série (a), et $D$
  de la lecture séquentielle de 256 Mio, un point par processus (b).
- [`figures/campaign-writes.pdf`](figures/campaign-writes.pdf) : fonction de répartition
  empirique des latences d'écriture d'un enregistrement de 4 Kio, avec ou sans demande
  de persistance (a) ; coût par enregistrement $t(k)/k$ selon $k$, avec le modèle
  $(F + w\,k)/k$ (confondu avec les médianes), le coût d'une écriture sans persistance
  et, légèrement décalé à droite du lot de 256, celui de 256 écritures suivies d'un
  seul `fsync` chronométré à part (b).

## 10. Résultats observés et interprétation

Médianes entre 10 processus, cœur P.

### 10.1 Lire : 1,35 µs depuis le cache, 58 µs depuis le disque

| Lecture de 4 Kio, pages au hasard | $\tilde t$ | IC 95 % | $t_{99}$ |
|---|---:|---:|---:|
| `rand_read_warm` | 1,35 µs | 1,30 à 1,37 | 2,54 µs |
| `rand_read_cold` | 58,0 µs | 57,9 à 58,1 | 88,6 µs |
| `rand_read_direct` | 54,8 µs | 54,7 à 54,9 | 63,7 µs |

- **Une page absente du cache coûte 43 fois plus** : $\tilde t_{\text{cold}}/\tilde
  t_{\text{warm}} = 43{,}1$ (de 40,8 à 46,1 selon le processus). Prédiction 1
  confirmée (1,35 µs) ; prédiction 2 confirmée pour la latence à froid (58 µs) et pour
  la queue ($t_{99}/\tilde t = 1{,}53$), **réfutée pour le rapport** (au moins 50
  prévu) : la lecture en cache est plus lente qu'imaginé, la lecture à froid proche de
  la borne basse.
- Les comptes confirment le mécanisme, pour chaque lecture à froid : une requête de
  lecture de 8 secteurs (4 Kio) au disque, 4 096 octets lus du stockage pour le
  processus, un changement de contexte volontaire (le processus dort pendant l'accès).
  Après l'échantillon, exactement 256 pages sont en cache : avec `POSIX_FADV_RANDOM`,
  aucune lecture anticipée. En cache : aucune requête, aucun sommeil.
- **Le cache de pages ajoute 3,3 µs à une lecture à froid** :
  $\tilde t_{\text{direct}}/\tilde t_{\text{cold}} = 0{,}945$ (prédiction 3 confirmée).
  Ce supplément correspond à l'allocation et à l'insertion de la page dans le cache,
  puis à la copie.
- Les fins de requête sont traitées sur le CPU du processus : la file `nvme0q8`,
  attachée au CPU 11, a reçu 1,75 million d'interruptions pendant la campagne, contre
  moins de 43 000 pour chacune des autres files.
- Contrôles : A/A de 0,990 à 1,008 par processus, contrôle positif de 1,987 à 2,009.
  Prédiction 4 confirmée.
- Hypothèse, non testée : 1,35 µs pour une lecture en cache, c'est 11,5 appels
  `getppid` de D1. La page est tirée au hasard dans 256 Mio : ni les structures du
  cache de pages qui la retrouvent, ni son contenu ne sont dans les caches du
  processeur. Quelques défauts de cache à environ 400 ns chacun, mesurés en C2,
  suffiraient.

### 10.2 Lire en séquence : la lecture anticipée double le débit de l'accès direct

| Lecture de 256 Mio par blocs de 128 Kio | $D$ | IC 95 % | Temps par bloc |
|---|---:|---:|---:|
| `seq_read_warm` | 5,42 Gio/s | 5,17 à 5,45 | 23 µs |
| `seq_read_cold` | 2,53 Gio/s | 2,52 à 2,53 | 48 µs |
| `seq_read_direct` | 1,35 Gio/s | 1,35 à 1,36 | 90 µs |

- Prédiction 5 confirmée pour les trois débits (dont deux près de la borne basse),
  **réfutée** pour l'écart entre cache et disque : $D_{\text{warm}}/D_{\text{cold}} =
  2{,}14$ au lieu d'au moins 3.
- **Pourquoi lire par le cache bat l'accès direct** : chaque bloc donne une requête de
  256 secteurs au disque dans les deux cas, mais le processus ne dort qu'une fois pour
  10 blocs (0,10 changement de contexte volontaire par bloc) quand la lecture anticipée
  travaille, contre une fois par bloc en `O_DIRECT`. Le disque lit le bloc suivant
  pendant que le programme copie le précédent. Ce résultat vaut pour des blocs de
  128 Kio lus par un seul fil ; il ne dit rien de l'accès direct avec de plus grands
  blocs ou plusieurs requêtes simultanées.
- Hypothèse, non testée : 5,4 Gio/s en cache, c'est 6 fois moins que la lecture de
  `/dev/zero` de D1 (34 Gio/s), qui écrit des zéros sans rien lire. Ici, 256 Mio sont
  lus depuis la mémoire vive sans tenir dans les caches du processeur : la limite
  serait la bande passante mémoire (C1).

### 10.3 Écrire : 4 µs sans persistance, 2 ms ou 7 ms avec

| Écriture d'un enregistrement de 4 Kio | $\tilde t$ | IC 95 % | $t_{99}$ | $v$ / $j$ |
|---|---:|---:|---:|---:|
| `tmpfs_append_fsync` | 1,99 µs | 1,97 à 2,02 | 6,4 µs | 0 / 0 |
| `append_buffered` | 3,86 µs | 3,80 à 4,09 | 12,6 µs | 0 / 0 |
| `overwrite_fdatasync` | 1,98 ms | 1,96 à 1,99 | 2,44 ms | 1 / 0 |
| `overwrite_odsync` | 1,96 ms | 1,95 à 1,98 | 2,45 ms | 1 / 0 |
| `overwrite_fsync` | 6,94 ms | 6,88 à 6,99 | 7,63 ms | 1 / 1 |
| `append_fdatasync` | 7,02 ms | 6,97 à 7,08 | 7,93 ms | 1 / 1 |
| `append_fsync`, $k = 1$ | 7,05 ms | 6,98 à 7,09 | 8,11 ms | 1 / 1 |

- **Demander la persistance multiplie le coût d'une écriture par 1 800** (ajout puis
  `fsync` contre `pwrite` seul), et par 3 600 par rapport au même `fsync` sur tmpfs, où
  il n'y a ni requête au disque ni sommeil. Prédictions 6 et 7 confirmées (dont
  $t_{\text{diff}} = 7{,}13$ ms pour le `fsync` final de 1 Mio).
- **Ce qui coûte, c'est la transaction du journal** : chaque demande de persistance
  envoie exactement un vidage au disque ($v = 1$), mais seules celles qui valident une
  transaction ($j = 1$) coûtent 7 ms ; les autres coûtent 2 ms.
  $\tilde t_{\text{overwrite fdatasync}}/\tilde t_{\text{overwrite fsync}} = 0{,}284$ :
  prédiction 8 **réfutée de peu**, l'écart est plus grand que prévu (borne basse 0,3).
- **Le seul changement des dates impose la transaction** : une réécriture avec `fsync`,
  qui ne change pas la taille, coûte 0,986 fois un ajout avec `fsync`. À l'inverse,
  `fdatasync` n'aide pas en fin de fichier (0,999) : la taille change et doit être
  journalisée. Prédiction 8 confirmée pour ce second rapport.
- `O_DSYNC` se comporte comme `write` puis `fdatasync` : même coût (0,997) et mêmes
  comptes. Prédiction 9 confirmée. Le constat du premier essai de contrôle (0 ou 1
  vidage pour 256 écritures `O_DSYNC`) **ne s'est pas reproduit** : $v = 1$ en médiane
  et 1,001 en moyenne sur les 200 échantillons des deux variantes `O_DSYNC`. Il reste
  inexpliqué.
- Secteurs écrits sur le disque par opération (médianes) : 8 (4 Kio) pour
  `overwrite_fdatasync`, 34 (17 Kio) pour `overwrite_fsync`, 59 (30 Kio) pour
  `append_fsync`. La transaction écrit donc quelques blocs de journal en plus, pour
  5 ms de plus.
- Contrôles : A/A de 0,992 à 1,043, contrôle positif de 2,008 à 2,096. Prédiction 11
  confirmée.
- Queues, toutes opérations confondues : 99,9ᵉ centile à 14,4 ms et maximum à 17,0 ms
  pour `append_fsync` ; 5,9 ms et 6,4 ms pour `overwrite_fdatasync`.
- Hypothèses, non testées : les 2 ms seraient le temps que met ce SSD grand public, sans
  protection contre les coupures, à rendre persistant son cache d'écriture (la durée
  des vidages n'a pas été enregistrée) ; les 5 ms de plus viendraient de la validation
  par le fil jbd2, dont le bloc final est, dans le code de jbd2 que je connais, écrit
  avec les drapeaux *preflush* et FUA, donc potentiellement deux points de persistance
  au lieu d'un. Ni les sources du noyau 7.0 ni un traçage n'ont été consultés pour le
  confirmer.

### 10.4 Regrouper : le coût d'un `fsync` est presque fixe

| $k$ (enregistrements par `fsync`) | 1 | 4 | 16 | 64 | 256 |
|---|---:|---:|---:|---:|---:|
| $t(k)$, durée d'un lot | 7,05 ms | 6,95 ms | 7,01 ms | 7,12 ms | 8,21 ms |
| $t(k)/k$, coût par enregistrement | 7,05 ms | 1,74 ms | 438 µs | 111 µs | 32,1 µs |

- **Écrire 256 enregistrements avant de demander la persistance coûte presque autant
  que d'en écrire un** : $F = 6{,}94$ ms et $w = 4{,}8$ µs, écart maximal du modèle aux
  médianes de 1,8 %. Par enregistrement, le lot de 256 coûte 0,0046 fois le lot de 1,
  soit environ 220 fois moins, mais encore 8 fois plus qu'une écriture sans
  persistance. Prédiction 12 confirmée ($F = 0{,}985\ t(1)$).
- Les comptes le montrent : un vidage et une transaction par lot, quelle que soit sa
  taille ; seuls les secteurs écrits augmentent (59 par lot de 1, 2 088 par lot de 256,
  soit 1 Mio de données et 40 secteurs de journal).
- **Peu importe quand les écritures ont eu lieu** : 256 `pwrite` seuls puis un `fsync`
  chronométré à part coûtent 1,012 fois le lot de 256 par enregistrement. Ce qui
  compte, c'est le nombre de demandes de persistance. Prédiction 13 confirmée.
- C'est la structure du modèle $S + b\,\ell$ de D1, avec un coût fixe 60 000 fois plus
  grand : 6,94 ms contre 116 ns pour entrer dans le noyau.

### 10.5 Grands folios : `write_bytes` ne compte pas les octets écrits sur le disque

Pour un fichier écrit d'un seul bloc de 1 Mio, chaque réécriture de 4 Kio ajoute
**1 Mio** à `write_bytes` de `/proc/self/io`, contre 4 Kio quand le fichier a été écrit
page par page. Le disque, lui, reçoit 8 secteurs (4 Kio) par opération dans les deux
cas, et la latence ne change pas : 1,009 fois pour `fdatasync`, 1,026 fois pour
`O_DSYNC` (prédiction 10 confirmée). `write_bytes` compte ce que le processus a sali
dans le cache, par folio entier, pas ce qui part vers le disque. L'explication par un
grand folio de 1 Mio est cohérente avec ces comptes, mais la taille des folios n'a pas
été observée directement.

### 10.6 Ce que D2 permet et ne permet pas de conclure

Permet, sur cette machine : le coût d'une lecture servie par le cache (1,35 µs) et par
le disque (58 µs) ; le coût d'une demande de persistance selon qu'elle exige une
transaction du journal (7 ms) ou non (2 ms) ; le caractère presque fixe de ce coût
jusqu'à 1 Mio par lot ; l'inutilité de `fdatasync` pour un ajout ; la correspondance,
par les comptes du noyau, entre chaque demande et ses requêtes au disque.

Ne permet pas : de savoir si les données sont réellement persistantes (aucune coupure
d'alimentation) ; de répartir les 58 µs ou les 7 ms entre disque, pilote, noyau et
réveil du processus (aucun traçage) ; de généraliser à un autre disque, en particulier
à un SSD avec protection contre les coupures, à un autre système de fichiers ou à
d'autres options d'ext4 ; de rien dire de plusieurs fils demandant la persistance en
même temps.

**Pour les 13 ms :** une lecture à froid (58 µs) en demanderait plus de 200 en série,
mais **deux demandes de persistance avec transaction du journal suffisent** (2 × 7 ms),
et une seule atteint déjà 14 ms au 99,9ᵉ centile. Contrairement aux appels système non
bloquants de D1, un `fsync` sur le chemin d'une requête est donc une explication
plausible des 13 ms, à vérifier dans J1 en observant si le serveur en fait.

## 11. Limites et expériences suivantes

- Un disque, un système de fichiers et ses options, un noyau, un cœur P ; campagne de
  20 min, fil unique, sans pression mémoire (256 Mio de fichier pour 5,9 Gio
  disponibles).
- Compteurs du disque et du journal communs à toute la machine : d'autres processus ont
  pu y contribuer (moyennes de 1,00 à 1,01 vidage par demande, au lieu d'exactement 1).
- Durée des vidages non enregistrée ; états de veille du processeur et du disque non
  contrôlés, par respect de la consigne de ne modifier aucun réglage global.
- Les écritures ne chronomètrent que l'opération : ni l'écriture différée des pages
  sales par le noyau, ni son effet sur d'autres processus.

Expériences suivantes :

1. Enregistrer la durée cumulée des vidages (champ 17 de `/sys/block/nvme0n1/stat`) et
   tracer une validation du journal (`ftrace` ou `blktrace`, qui demandent votre
   accord) pour tester les hypothèses de la section 10.3.
2. Plusieurs fils qui appellent `fsync` en même temps sur des fichiers différents :
   jbd2 devrait regrouper leurs transactions, et le coût par demande baisser (lien avec
   F et G).
3. Écritures `O_DIRECT` avec `O_DSYNC`, qui peuvent porter le drapeau FUA au lieu d'un
   vidage séparé.
4. **E, comparaison entre langages** : prochaine partie du programme.

## 12. Compréhension et prolongement

Questions :

1. Pourquoi une lecture en `O_DIRECT` est-elle plus rapide qu'une lecture à froid par
   le cache pour 4 Kio, mais deux fois plus lente pour lire un fichier entier par blocs
   de 128 Kio ?
2. Pourquoi une réécriture suivie de `fsync` coûte-t-elle autant qu'un ajout, alors que
   la taille du fichier ne change pas ?
3. `fdatasync` coûte 3,5 fois moins que `fsync` en réécriture, mais pas en fin de
   fichier. Qu'est-ce qui distingue les deux cas pour le système de fichiers ?
4. Écrire 256 enregistrements puis appeler `fsync` coûte 8 ms ; appeler `fsync` après
   chacun coûte 1,8 s. Que faut-il accepter pour obtenir le premier coût, et que
   perd-on en cas de coupure ?
5. Pourquoi `write_bytes` ne mesure-t-il pas les octets envoyés au disque ?

Prolongement : un journal d'application écrit des enregistrements de 256 octets à
1 000 par seconde et doit garantir qu'aucun enregistrement plus vieux que 10 ms n'est
perdu. À partir de $F$ et $w$, prédire le coût par enregistrement d'une validation
toutes les 10 ms, puis le mesurer avec le harnais en ajoutant un lot de 10
enregistrements de 256 octets.
