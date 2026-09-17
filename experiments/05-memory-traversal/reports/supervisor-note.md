# Fiche superviseur - parcours mémoire

**Nous cherchions à savoir** comment le coût d'un accès mémoire et le débit de
lecture évoluent avec la taille des données et l'ordre des accès, et s'il est
possible d'attribuer une transition de coût à un niveau de cache autrement que par
la forme d'une courbe.

**Nous prévoyions**, sur un cœur P, un parcours séquentiel peu sensible à la
taille, avec un débit de 5 à 15 Gio/s ; des accès aléatoires coûtant 40 à 200 ns à
256 Mio ; des transitions près des tailles annoncées des caches L1d, L2 et L3. Un
contrôle était fixé à l'avance : le cœur LP-E n'ayant pas de cache L3, le rapport
$G = c(16\ \text{Mio}) / c(1\ \text{Mio})$, où $c$ est le coût d'un accès aléatoire
pour une taille de données donnée, devait y être au moins deux fois plus grand que
sur les cœurs P et E, faute de quoi l'attribution au L3 serait abandonnée.

**Nous avons mesuré**, sur le cœur P, un coût identique pour tous les ordres
d'accès tant que les données tiennent dans 1 Mio (1,1 à 1,6 ns), puis, à 256 Mio,
2,1 ns en séquentiel et 16,8 ns en aléatoire. Le débit séquentiel n'a pas dépassé
5,5 Gio/s : la boucle de mesure limitait, pas la mémoire. Les accès aléatoires
indépendants coûtent bien moins que la latence d'accès attendue, parce que le
processeur traite plusieurs défauts de cache en parallèle ; à 256 Mio, le cœur
LP-E est 2,8 fois plus lent que le cœur P. Aucune transition n'apparaît près du
L1d. Le contrôle d'attribution a échoué : $G$ vaut 7,9 (P), 6,2 (E) et 11,0
(LP-E), soit un rapport de 1,4 et 1,8 au lieu d'au moins 2. Lire 16 octets à
cheval sur deux lignes de cache coûte 1,3 à 2,3 fois plus que dans une seule
ligne à 256 Mio.

**Le protocole était** un programme C compilé par GCC `-O2` ; 33 tailles de 4 Kio
à 256 Mio par demi-octaves ; 9 parcours (séquentiel, trois pas constants,
aléatoire, deux paires de lectures, contrôles A/A et positif) ; $2^{20}$ accès par
échantillon ; pages de 4 Kio imposées au seul processus ; 8 processus
indépendants par cœur (P, E, LP-E), épinglés, dans un ordre aléatoire fixé ; 9
tours dont le premier jeté. Les 64 152 résultats ont été vérifiés par une
référence indépendante et recalculables en Python.

**Les résultats montrent** que la localité ne compte qu'au-delà d'environ 1 Mio
sur ce montage, qu'un parcours aléatoire à indices indépendants mesure une
capacité de traitement en parallèle et non une latence, et que l'alignement d'une
lecture sur les lignes de cache compte. Ils montrent aussi qu'une coïncidence entre
une transition et une taille de cache ne suffit pas : notre critère d'attribution,
fixé avant la mesure, a échoué, et une explication concurrente (traductions
d'adresses avec des pages de 4 Kio) reste ouverte.

**Les limites sont** l'absence de compteurs matériels, les préchargeurs non
contrôlables, un seul CPU par type de cœur, une charge de fond plus élevée que
lors des campagnes précédentes, et une boucle séquentielle trop lente pour mesurer
la bande passante de la mémoire vive.

**L'expérience suivante sera** C2 : accès dépendants (liste chaînée) pour mesurer
une latence que le processeur ne peut pas paralléliser, et comparaison des pages
de 4 Kio et de 2 Mio pour séparer TLB et caches. Pour les 13 ms, il faudrait
environ 800 000 accès aléatoires lointains pour les atteindre sur le cœur P.
