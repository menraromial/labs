# Fiche superviseur - accès dépendants

**Nous cherchions à savoir** combien coûte un accès lointain à la mémoire quand le
processeur ne peut pas en recouvrir plusieurs, quelle part de la montée des coûts
observée en C1 revient à la traduction d'adresses (TLB) plutôt qu'aux caches, et
combien coûte le premier accès à une mémoire neuve.

**Nous prévoyions**, sur le cœur P, 250 à 600 ns par accès dépendant lointain et un
rapport de 10 à 40 avec les accès indépendants, plus faible sur le cœur LP-E ; une
liste chaînée contiguë presque aussi rapide que dans le cache ; avec des pages de
2 Mio, un contrôle d'attribution au L3 réussi (`G(LP-E) ≥ 2 × G(P)`) et une
transition de C1 réduite d'au moins 40 % ; enfin 0,3 à 3 µs par défaut de page de
4 Kio, et un premier accès 2 à 15 fois moins cher par Mio en pages de 2 Mio.

**Nous avons mesuré** 380 à 455 ns par accès dépendant lointain, presque identiques
sur les cœurs P et LP-E, soit environ quatre fois l'ordre de grandeur supposé en
C1. Les accès indépendants coûtent 16 à 20 fois moins sur le cœur P et 9 à 12 fois
moins sur le cœur LP-E : le cœur P recouvre une vingtaine de défauts de cache. Une
liste chaînée contiguë coûte 4 ns, moins de 1 % de la liste dispersée. Les pages
géantes réduisent de 11 à 36 % le coût des accès à 256 Mio. Les deux contrôles
fixés à l'avance échouent : `G(LP-E) / G(P)` vaut 1,61 et la transition n'est
réduite que de 20 %. Un défaut de page de 4 Kio coûte environ 2 µs ; avec des pages
de 2 Mio, le premier accès coûte 2,3 à 3,5 fois moins par Mio.

**Le protocole était** un programme C compilé par GCC `-O2` ; 17 tailles de 4 Kio à
256 Mio ; un cycle aléatoire unique (Sattolo) et une liste contiguë par taille ;
accès dépendants, accès indépendants, contrôles A/A et positif, premier et second
accès à des zones neuves de 16 et 256 Mio ; pages de 4 Kio ou 2 Mio demandées par
processus ; 8 processus indépendants par combinaison de cœur (P, LP-E) et de taille
de page, épinglés, dans un ordre aléatoire fixé ; 11 tours dont le premier jeté.
Les 30 624 résultats ont été vérifiés, et la part de pages géantes obtenue a été
mesurée (100 %).

**Les résultats montrent** que la dispersion des adresses, et non la dépendance
seule, rend un accès coûteux, et que des accès indépendants mesurent un débit, pas
une latence. Ils montrent aussi que ni le L3 ni la TLB n'expliquent, selon nos
critères, la montée des coûts entre 1 et 16 Mio ; la plus forte hausse se situe
entre 2 et 4 Mio sur les deux cœurs, dont le L2 annoncé est de 2 Mio.

**Les limites sont** l'absence de compteurs matériels, un L3 partagé avec toute la
machine, une mémoire vive dont le type est inconnu, et des contrôles moins bons que
dans les projets précédents (A/A de 0,95 à 1,08 sur le cœur P, contrôle positif
systématiquement sous 2) : les écarts de moins de 10 % sont à lire avec prudence.

**L'expérience suivante sera** D1 (appels système et traitement par lots). Pour les
13 ms, C2 fournit une hypothèse forte à tester en J2 : environ 6 500 défauts de page
(25 Mio de mémoire neuve) ou 29 000 accès dépendants lointains suffisent à les
atteindre, ce qu'une première requête dans un processus neuf pourrait provoquer.
