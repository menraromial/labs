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

