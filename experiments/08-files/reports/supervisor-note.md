# Fiche superviseur - fichiers et persistance

**Nous cherchions à savoir** ce que coûte une lecture servie par le cache de pages
comparée à une lecture qui attend le disque, ce que coûte une écriture confiée au
noyau comparée à une écriture dont on demande la persistance, et ce que rapporte le
regroupement de ces demandes.

**Nous prévoyions**, sur le cœur P : 0,3 à 2 µs par lecture de 4 Kio en cache, 50 à
300 µs sans cache, soit au moins 50 fois plus ; un débit séquentiel au moins 3 fois
plus élevé en cache ; 1 à 10 µs par écriture sans persistance, 0,5 à 10 ms avec
`fsync` ; `fdatasync` en réécriture à 0,3 à 0,9 fois `fsync` ; un coût de `fsync`
presque fixe, le lot de 256 enregistrements coûtant au plus 1/20 du lot de 1 par
enregistrement.

**Nous avons mesuré** 1,35 µs par lecture en cache et 58 µs sans cache (43 fois plus,
une requête au disque et un sommeil par lecture) ; 5,4 Gio/s en séquence depuis le
cache, 2,5 Gio/s depuis le disque avec lecture anticipée et 1,35 Gio/s en
`O_DIRECT`. Écrire 4 Kio coûte 3,9 µs sans persistance ; 7,0 ms avec `fsync`, en
ajout comme en réécriture, et 2,0 ms avec `fdatasync` ou `O_DSYNC` en réécriture :
chaque demande envoie un vidage au disque, mais seules celles qui valident une
transaction du journal coûtent 7 ms. Un `fsync` coûte 6,94 ms plus 4,8 µs par
enregistrement du lot : 32 µs par enregistrement pour 256 par `fsync`. Les
prédictions tiennent sauf trois : le rapport des lectures aléatoires (43 au lieu
d'au moins 50), celui des lectures séquentielles (2,1 au lieu d'au moins 3) et
le rapport de `fdatasync` à `fsync` en réécriture (0,284, sous la borne de 0,3).

**Le protocole était** un programme C compilé par GCC `-O2` ; 23 mesures (lectures
séquentielles et aléatoires en cache, sans cache et en `O_DIRECT` ; écritures sans
persistance, avec `fsync`, `fdatasync` ou `O_DSYNC`, en ajout ou en réécriture, par
lots de 1 à 256, et témoin sur tmpfs) ; 10 processus épinglés sur le CPU 11 ; 11 tours
dont le premier jeté, ordre aléatoire fixé. Sans vider les caches système : seules
les pages de notre fichier étaient retirées du cache, contrôlé par `mincore`. Pour
chacun des 2 530 échantillons ont été vérifiés le contenu de chaque bloc lu et de
chaque enregistrement relu en `O_DIRECT`, l'état du cache, et les appels et octets
comptés par le noyau ; les requêtes, vidages du disque et transactions du journal
ont été relevés.

**Les résultats montrent** que le coût d'une écriture persistante est dominé par un
coût fixe par demande, fixé par la validation du journal plus que par la quantité de
données : ce qui compte est le nombre de demandes de persistance, pas le nombre
d'écritures. Ils montrent aussi que la lecture anticipée permet au disque de
travailler pendant que le programme copie, et que `write_bytes` de
`/proc/self/io` compte les folios salis, pas les octets écrits sur le disque.

**Les limites sont** l'impossibilité de vérifier la persistance elle-même, un seul
disque grand public sans protection contre les coupures, des compteurs du disque
partagés avec toute la machine, l'absence de traçage pour répartir les 7 ms entre
disque et noyau (hypothèses de la section 10.3 non testées), et un fil unique.

**L'expérience suivante sera** la partie E, comparaison entre langages. Pour les
13 ms : deux `fsync` avec transaction du journal (2 × 7 ms) suffisent, alors qu'il
faudrait plus de 200 lectures à froid ; une demande de persistance sur le chemin
d'une requête est donc une explication plausible, que J1 devra rechercher.
