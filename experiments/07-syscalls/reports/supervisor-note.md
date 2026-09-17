# Fiche superviseur - appels système

**Nous cherchions à savoir** ce que coûte un passage de l'espace utilisateur au
noyau sur cette machine, quelle part de ce coût est fixe par appel et quelle part
dépend des octets traités, et ce que rapportent un tampon de la bibliothèque C ou
un tampon manuel.

**Nous prévoyions**, sur le cœur P : 50 à 250 ns pour un appel système minimal,
dont l'essentiel en entrée et sortie du noyau ; `clock_gettime` 3 à 15 fois plus
cher par appel système que par le vDSO ; un coût fixe indépendant du bloc pour
`/dev/null` et un coût par octet de 0,03 à 0,2 ns pour `/dev/zero`, avec un
croisement entre 1 et 16 Kio ; `fwrite` au moins 10 fois plus rapide qu'un `write`
par enregistrement, et un tampon manuel de 0,3 à 1 fois `fwrite` ; une part du
temps système d'au moins 70 % pour les petits appels.

**Nous avons mesuré** 116 ns pour `getppid` (166 ns sur le cœur E, 140 ns sur le
cœur LP-E), dont 93 % pour la seule entrée-sortie (un appel inexistant coûte
109 ns) ; `clock_gettime` 7,4 fois plus cher par appel système que par le vDSO sur
les trois cœurs. `/dev/null` coûte 157 ns par appel de 1 octet à 1 Mio ;
`/dev/zero` a un coût fixe de 173 ns et 0,022 ns par octet, soit un croisement vers
7,7 Kio. `fwrite` est 12,3 fois plus rapide qu'un `write` par enregistrement, mais un
tampon manuel est encore 7,6 fois plus rapide que `fwrite` : les appels système n'y
pèsent plus que 0,6 ns sur 12,8 ns par enregistrement. La part du temps système
mesurée par `getrusage` s'est révélée invalide (25 % pour un simple appel de
fonction).

**Le protocole était** un programme C compilé par GCC `-O2` ; 33 mesures (entrée
dans le noyau, blocs de 1 octet à 1 Mio sur `/dev/null` et `/dev/zero`,
enregistrements écrits de quatre façons) ; 10 processus indépendants par cœur (P, E,
LP-E), épinglés, dans un ordre aléatoire fixé ; 11 tours dont le premier jeté. Pour
chacun des 10 890 échantillons, le résultat et le nombre d'appels `read` et `write`
compté par le noyau (`/proc/self/io`) ont été vérifiés.

**Les résultats montrent** qu'un appel système simple coûte environ 200 appels de
fonction, que ce coût est presque entièrement fixe, et que le regrouper est rentable
jusqu'à quelques Kio par appel quand le noyau copie les données. Ils montrent aussi
qu'un tampon de bibliothèque déplace le coût dominant vers l'appel de bibliothèque
lui-même.

**Les limites sont** l'absence de lecture fiable du temps système à l'échelle de la
milliseconde (répartition par ticks cumulés depuis le début du processus), des
fichiers spéciaux sans stockage ni cache de pages, des atténuations Spectre fixées,
et un contrôle A/A qui dépasse de quelques millièmes sur deux cœurs.

**L'expérience suivante sera** D2 : écriture mise en tampon par le noyau contre
`fsync`, et lecture servie par le cache de pages. Pour les 13 ms : il faudrait
environ 110 000 appels système non bloquants ; les appels système ne deviennent une
explication plausible que s'ils attendent, ce que D2 et J1 examineront.
