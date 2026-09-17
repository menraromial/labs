# Fiche superviseur - dépendances et branchements

**Nous cherchions à savoir** pourquoi deux boucles au même nombre d'instructions
peuvent avoir des coûts très différents : que coûtent, sur cette machine, une
dépendance entre itérations et un branchement imprévisible, et que change la forme
donnée par le compilateur à une condition.

**Nous prévoyions**, après lecture de l'assembleur des 6 binaires : un rapport de
2,5 à 4,5 entre deux boucles qui ne diffèrent que par la place d'une
multiplication ; un coût en cloche selon la part `p` d'éléments retenus pour un
branchement, avec au moins un facteur 5 entre données mélangées et triées ; une
pénalité de 5 à 15 ns par mauvaise prédiction ; un coût plat pour les versions
`cmov`, masque ou sans branchement ; enfin, un surcoût localisé pour les boucles
de 32 à 128 itérations, qui expliquerait une observation de B1.

**Nous avons mesuré** un rapport de 3,0 entre `h = (h ^ x) * K` et `h ^= x * K`
(1,61 contre 0,54 ns par élément), la première boucle gardant le même coût dans
les 6 binaires, faute de pouvoir être vectorisée. Sur le même multiensemble de
valeurs et le même code machine, un filtre à branchement coûte 5,7 ns par
élément en ordre aléatoire et 0,41 ns trié (facteur 14), avec une pénalité
ajustée de 9,4 à 10,9 ns par mauvaise prédiction (R² ≥ 0,94). La même
condition écrite avec `if` n'est sensible aux données que dans l'un des 6 binaires ;
les autres produisent un `cmov` ou un masque. La version sans branchement reste à
0,41 à 0,45 ns quel que soit l'ordre. Pour les petites boucles, le coût d'un appel
fait un saut unique d'environ 11 ns entre 32 et 48 itérations chez GCC, égal à la
pénalité mesurée indépendamment.

**Le protocole était** 6 binaires (GCC 15.2 et Clang 21.1 ; scalaire, -O2, -O3
AVX2) partageant un harnais compilé une fois ; 15 processus indépendants par
binaire, ordre aléatoire fixé, épinglés sur un cœur P ; 21 tours dont le premier
jeté, 53 mesures dans un ordre tiré à chaque tour ; données des branchements
remélangées avant chaque échantillon, hors chronométrage. Les 100 170 résultats
et tous les tampons de sortie ont été vérifiés.

**Les résultats montrent** que la structure de dépendance et la prévisibilité des
branchements dominent le coût d'une boucle, bien plus que le nombre
d'instructions, et que la forme d'une condition dépend du compilateur. Le saut de
coût entre 32 et 48 itérations est cohérent avec une sortie de boucle mal prédite
une fois par appel au-delà d'une trentaine d'itérations, ce qui explique le
surcoût observé en B1.

**Les limites sont** l'absence de compteurs matériels : mauvaises prédictions et
cycles sont inférés de durées, pas comptés. Les données sont synthétiques et
indépendantes, et un seul processeur a été étudié. Trois observations restent
inexpliquées : aux `p` intermédiaires, un taux apparent de mauvaises prédictions
supérieur à celui d'un vote majoritaire ; la compensation du saut entre 48 et
256 itérations ; le faible coût des appels courts chez Clang.

**L'expérience suivante sera** C1 (parcours mémoire et bande passante). Un
comptage direct des mauvaises prédictions demanderait d'abaisser temporairement
`perf_event_paranoid`, ce qui ne sera fait qu'avec accord explicite. Pour les
13 ms : il faudrait plus d'un million de mauvaises prédictions pour les atteindre,
ce qui reste à vérifier dans le code d'origine plutôt qu'à supposer.
