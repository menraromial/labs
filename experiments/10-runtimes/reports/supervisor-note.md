# Fiche superviseur - environnements d'exécution

**Nous cherchions à savoir** ce qui se passe avant et autour du calcul : combien coûte le
démarrage d'un programme selon son environnement d'exécution et où part ce temps, combien
de temps un JIT met à atteindre son régime établi, et ce que coûtent, en débit et en
pauses, les ramasse-miettes face à une allocation continue.

**Nous prévoyions** un exécutable C statique 1,4 à 3 fois plus rapide à démarrer que
dynamique, un démarrage de 20 à 60 ms pour Node et de 30 à 80 ms pour la JVM ; une JVM
rejoignant C à 50 % près après un premier pas au moins 5 fois plus lent, V8 à 2 fois près
sur les flottants ; un échauffement réduit d'un tiers sur deux cœurs ; un JIT de CPython
entre -15 et +10 % ; des pauses de collecte au moins 10 fois la durée d'un lot ordinaire
en Java et Node, 3 fois en Python, avec un coût d'allocation de 5 à 30 ns en Java.

**Nous avons mesuré** un démarrage de 0,58 ms en C statique contre 0,73 ms dynamique,
17 ms pour CPython (dont 6,4 ms pour importer `site`), 31 ms pour Node, 59 ms pour la JVM
(48 ms pour créer la machine virtuelle, 17 ms de plus sans archive CDS) et 92 ms avec
NumPy. HotSpot rejoint exactement C (rapport 1,000) dès le 3ᵉ à 6ᵉ pas, après un premier
pas 14 à 26 fois plus lent ; V8 atteint 1,14 fois C sur les flottants et 4,1 fois sur une
chaîne en `BigInt`, mais 6 processus sur 20 rebasculent ensuite vers un régime 14 fois
plus lent. Deux cœurs ne réduisent pas nettement l'échauffement. Le JIT de CPython gagne
7 à 8 %. Pour allouer un objet et en abandonner un avec 1 million d'objets vivants : C
9,4 ns ; Go 42 ns (31 ns avec `GOGC=400`, mais 1,8 fois plus de mémoire), lots jusqu'à
8,5 ms alors que Go déclare 0,14 ms de pauses ; Java 50 à 62 ns, pauses jusqu'à 146 ms
(Serial) ou 61 ms (G1) ; Node 130 ns, 1 % des lots au-delà de 43 ms ; CPython 187 ns et
aucune collecte, avec ou sans `gc`.

**Le protocole était** des programmes équivalents en C, Rust, Go, Java 17, Node 26 et
CPython 3.14, aux résultats vérifiés au bit près ; 12 commandes de démarrage répétées
50 fois dans un ordre aléatoire, avec les traces de décomposition de chaque
environnement ; 9 modes d'échauffement (avec ou sans JIT, un ou deux cœurs) et 8 modes
d'allocation, 10 processus indépendants chacun, épinglés, dans un ordre aléatoire fixé ;
toutes les options propres à chaque processus, aucun réglage global.

**Les résultats montrent** que le démarrage des environnements à JIT ou interprétés
(17 à 92 ms) dépasse à lui seul les 13 ms étudiés, qu'un JIT peut égaler C mais après un
échauffement et parfois avec un régime instable, et que le coût d'un ramasse-miettes
dépend de la durée de vie des objets : les pires lots vont de 8,5 à 146 ms. Ils montrent
aussi que les pauses déclarées par un environnement ne mesurent pas la latence subie.

**Les limites sont** une version et des réglages par défaut pour chaque environnement,
un seul CPU pour l'allocation (défavorable aux collecteurs concurrents), des compteurs de
collectes aux définitions différentes, et un surcoût d'échauffement qui additionne aussi
le bruit (plancher de 5 à 10 pas sans JIT). Sont notamment réfutés le gain du lien
statique, le coût de l'interpréteur Java et les coûts d'allocation de Java et de Node, ainsi que l'effet de deux cœurs et celui de `gc.disable()`.

**L'expérience suivante sera** F1 (processus et threads). Pour les 13 ms, E2 ajoute trois
hypothèses à tester en J2 : démarrage d'un environnement neuf, première requête exécutée
avant la fin de l'échauffement, collecte pendant la requête.
