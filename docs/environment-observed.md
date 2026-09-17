# Diagnostic initial de l'environnement

Observation effectuée le 2026-09-16 depuis le terminal accessible au laboratoire.
Aucun benchmark de durée n'a encore été exécuté.

## Faits observés

- Système : Ubuntu 26.04.1 LTS, noyau Linux `7.0.0-31-generic`.
- Architecture : x86-64, little-endian.
- CPU présenté au processus : Intel Core Ultra 7 165H, 22 processeurs logiques,
  16 cœurs annoncés par `lscpu`, un socket, un nœud NUMA.
- Fréquence annoncée : plage de 400 MHz à 5 GHz. Une fréquence instantanée ou
  maximale ne donne pas un nombre d'« opérations utiles par seconde » : plusieurs
  instructions peuvent avancer en parallèle, certaines prennent plusieurs cycles,
  et mémoire, dépendances et branches peuvent retarder l'exécution.
- Caches annoncés par `lscpu` : L1d 544 KiB (14 instances), L1i 896 KiB
  (14 instances), L2 18 MiB (9 instances), L3 24 MiB (1 instance).
- Mémoire visible : 14 GiB, sans swap au moment de l'observation.
- Source d'horloge noyau courante : `tsc`; `acpi_pm` est aussi disponible.
- Compilateurs/runtimes : GCC 15.2, Clang 21.1.8, Python 3.14.4,
  Rust/Cargo 1.85.0, Go 1.26.0, OpenJDK 17.0.20, Node.js 26.7.0.
- Outils présents : `perf`, `strace`, `taskset`, `ss`, `pidstat`, `time`,
  `make`, `cmake`.
- Politique `perf_event_paranoid` : `4`. Les compteurs matériels seront
  vraisemblablement indisponibles sans permission supplémentaire ; cela devra
  être testé sans supposer le résultat.
- `systemd-detect-virt` répond `container-other` et le processus appartient à une
  portée de l'éditeur (`app-code-…scope`).

## Compléments observés pendant A2

- Topologie hybride annoncée par le noyau : CPU 0 à 11 dans `cpu_core` (P,
  fréquence maximale 4,7 ou 5,0 GHz), CPU 12 à 21 dans `cpu_atom`. Parmi eux,
  les CPU 20 et 21 n'ont pas de cache L3 et plafonnent à 2,5 GHz ; nous les
  notons LP-E, les autres E (3,8 GHz). Cette correspondance est une interprétation.
- Pilote `intel_pstate`, gouverneur `powersave`, préférence énergétique `power`.
- `perf stat` refuse même l'événement logiciel `task-clock` : aucun compteur n'est
  accessible sans modifier `perf_event_paranoid` ou les capacités du processus.

## Compléments observés pendant C1

- Caches annoncés par CPU (`/sys/devices/system/cpu/cpu*/cache`) : cœur P
  (CPU 11) L1d 48 Kio, L2 2 Mio partagé avec son frère d'hyperthreading, L3
  24 Mio partagé par les CPU 0 à 19 ; cœur E (CPU 19) L1d 32 Kio, L2 2 Mio partagé
  par les CPU 16 à 19, même L3 ; cœur LP-E (CPU 21) L1d 32 Kio, L2 2 Mio partagé
  avec le CPU 20, **aucun L3**.
- Pages de 4 Kio ; pages géantes transparentes en mode `madvise` (et `defrag`
  en mode `madvise`) ; pages géantes de 2 Mio disponibles.
- Mémoire disponible au moment de C1 : environ 4,9 Gio sur 14,5 Gio.

## Compléments observés pendant C2

- Pages géantes de 2 Mio obtenues à 100 % pendant la campagne pour les zones
  demandées avec `MADV_HUGEPAGE`, mais partiellement refusées pendant la mise au
  point : leur disponibilité dépend de l'état de la mémoire.
- Latence d'un accès lointain non recouvert : environ 400 ns, sur les cœurs P et
  LP-E. Le type de mémoire vive n'est pas identifiable sans droits
  d'administration (`dmidecode`).
- Défaut de page mineur en pages de 4 Kio, mise à zéro comprise : environ 2 µs.

## Compléments observés pendant D1

- Atténuations actives : Spectre v2 par IBRS amélioré, IBPB conditionnel, BHI ;
  Meltdown non concerné ; VMScape atténué par IBPB avant le retour en espace
  utilisateur. Le noyau est compilé avec `CONFIG_MITIGATION_PAGE_TABLE_ISOLATION`,
  sans effet attendu sur un processeur non concerné par Meltdown.
- `CONFIG_HZ=1000` et `CONFIG_VIRT_CPU_ACCOUNTING_GEN=y`, mais sans `nohz_full` sur
  la ligne de commande : temps utilisateur et système répartis par échantillonnage
  au tick, inutilisables sur des fenêtres de quelques millisecondes.
- Glibc : tampon de 4 Kio choisi par `fwrite` pour `/dev/null`
  (`st_blksize` = 4 096).
- `/proc/self/io` compte exactement les appels `read` et `write` d'un processus,
  sans privilège.

## Compléments observés pendant D2

- Stockage : ext4 (`data=ordered`, `delalloc`, `barrier`, `commit=5`,
  `nodiscard`) sur LVM (`dm-0`), sur un SSD NVMe Samsung `MZVL21T0HCLR` de 1 To
  (micrologiciel `HPS4NGXH`), ordonnanceur d'entrées-sorties `none`, cache
  d'écriture volatile (`write back`) et FUA annoncés, lecture anticipée de 128 Kio.
  `/dev/shm` et `/tmp` sont des tmpfs de 7,3 Gio.
- Écriture différée : `vm.dirty_ratio` 20, `vm.dirty_background_ratio` 10,
  `vm.dirty_expire_centisecs` 3 000.
- Lecture de 4 Kio : 1,35 µs depuis le cache de pages, 58 µs depuis le disque,
  54,8 µs en `O_DIRECT` (cœur P). Lecture séquentielle de 256 Mio : 5,4 Gio/s en
  cache, 2,5 Gio/s depuis le disque, 1,35 Gio/s en `O_DIRECT`.
- Persistance : chaque `fsync` ou `fdatasync` envoie un vidage au disque ; 7,0 ms
  quand une transaction du journal est validée (ajout, ou réécriture avec `fsync`),
  2,0 ms sinon (réécriture avec `fdatasync` ou `O_DSYNC`). Coût d'un `fsync` :
  6,94 ms plus 4,8 µs par enregistrement de 4 Kio du lot.
- Les fins de requête NVMe sont traitées sur la file du CPU qui les soumet
  (`nvme0q8` pour le CPU 11).
- Le noyau utilise de grands folios dans le cache de pages d'ext4 : `write_bytes`
  compte 1 Mio par réécriture de 4 Kio d'un fichier écrit d'un seul bloc de 1 Mio.

## Compléments observés pendant E1

- Chaînes disponibles : GCC 15.2, Clang 21.1, `rustc` 1.85.0 (LLVM 19.1.7, installé par
  `rustup` dans `~/.cargo`), Go 1.26.0 (`GOAMD64=v1`), CPython 3.14.4 (GIL actif, JIT
  disponible mais désactivé), NumPy 2.3.5 lié à OpenBLAS (variante `pthread`).
- À travail équivalent, C, Rust et Go coûtent la même chose à 4 % près sur le CPU 11 ;
  CPython coûte 30 à 78 fois C selon la charge.
- Démarrage d'un programme qui se termine aussitôt : 0,6 à 0,9 ms en C et en Rust,
  1,5 ms en Go, 19,8 ms pour CPython, 99,7 ms avec `import numpy`.

## Compléments observés pendant E2

- Environnements supplémentaires : OpenJDK 17.0.20 (HotSpot, G1 par défaut, tas maximal
  estimé à 3,64 Gio ; `javac` 25 utilisé avec `--release 17`), Node 26.7.0 (V8 14.6),
  LuaJIT présent ; ni PyPy ni .NET.
- Démarrage d'un programme vide : 0,58 ms (C statique), 0,73 ms (C dynamique), 0,96 ms
  (Rust), 1,2 ms (Go), 17 ms (CPython), 31 ms (Node), 59 ms (JVM), 92 ms (CPython avec
  NumPy).
- La JVM écrit ses durées avec une virgule décimale selon la locale : forcer `LC_ALL=C`
  pour analyser `-Xlog`.

## Ce que ces faits ne garantissent pas

- La topologie hybride exacte des cœurs performants/efficaces n'est pas encore
  établie. Les nombres d'instances de cache et de threads par cœur montrent que
  la valeur synthétique « 2 threads par cœur » ne suffit pas à la décrire.
- La présence des instructions de virtualisation VT-x signifie que le processeur
  les supporte, pas que notre programme s'exécute dans une VM.
- La détection `container-other` indique une forme d'isolation, mais ne permet pas
  à elle seule de conclure « conteneur classique », VM ou machine physique.
  Le modèle du CPU hôte semble exposé, mais la nature exacte reste incertaine.
- La résolution annoncée d'une horloge, son coût de lecture et la précision réelle
  d'une mesure sont trois propriétés distinctes. Elles restent à mesurer.
- Les fréquences, la charge concurrente et les limites de ressources au moment
  d'une future campagne ne sont pas décrites par ce relevé initial.

## Diagnostic pédagogique provisoire

Le niveau académique est avancé, mais le point de départ déclaré est débutant en
architecture, noyau et méthodologie de performance. La première compétence à
construire n'est donc pas l'emploi d'un profileur : c'est la capacité à définir
précisément une grandeur, le périmètre chronométré et les explications alternatives.
Le niveau en C et en Linux reste à observer dans les exercices, plutôt qu'à deviner.
