# Glossaire

- **Temps écoulé** (*elapsed time*, *wall-clock time*) : durée perçue entre deux
  instants. Elle inclut les périodes où le programme ne s'exécute pas sur un CPU.
- **Temps CPU** (*CPU time*) : temps pendant lequel le CPU exécute effectivement
  le processus en espace utilisateur ou pour lui dans le noyau.
- **Horloge monotone** (*monotonic clock*) : horloge qui ne recule pas ; elle est
  adaptée aux durées, contrairement à l'heure civile qui peut être corrigée.
- **Résolution** (*resolution*) : plus petit pas représentable ou annoncé par une
  horloge. Ce n'est ni son exactitude ni son coût de lecture.
- **Précision** (*precision*) : finesse et reproductibilité d'une mesure.
- **Exactitude** (*accuracy*) : proximité entre la mesure et la valeur vraie.
- **Latence** (*latency*) : durée nécessaire à une opération ou une requête.
- **Débit** (*throughput*) : quantité de travail terminée par unité de temps.
- **Cycle CPU** (*CPU cycle*) : battement de l'horloge d'un cœur. Une instruction
  n'équivaut pas nécessairement à un cycle, ni un cycle à une instruction.
- **Microbenchmark** (*microbenchmark*) : mesure d'une opération très courte,
  isolée de l'application.
- **Lot** (*batch*) : plusieurs opérations entre deux lectures d'horloge, pour
  partager le coût fixe du chronométrage.
- **Répétition** (*repetition*) : nouvelle mesure dans le même processus.
- **Exécution indépendante** (*independent run*) : nouvelle mesure dans un
  nouveau processus, qui peut rencontrer un autre cœur ou un autre état machine.
- **Échauffement** (*warm-up*) : période initiale dont les coûts diffèrent du
  régime établi. Sa durée se mesure ; elle ne se suppose pas.
- **Premier passage à froid** (*cold path*, *first-call cost*) : surcoût de la
  première exécution d'un chemin de code dans un processus.
- **Biais d'ordre** (*order bias*) : écart systématique dû à la position d'une
  variante dans la séquence de mesure.
- **Entrelacement** (*interleaving*) : alternance des variantes à chaque tour,
  dans un ordre tiré au hasard.
- **Contrôle négatif, test A/A** (*negative control*, *A/A test*) : comparaison
  d'une variante à elle-même ; tout écart mesure l'erreur du protocole.
- **Contrôle positif** (*positive control*) : comparaison à une variante dont
  l'écart est connu par construction.
- **Intervalle de confiance bootstrap** (*bootstrap confidence interval*) :
  intervalle obtenu en rééchantillonnant avec remise les unités indépendantes.
- **Affinité CPU** (*CPU affinity*) : CPU logiques sur lesquels un processus peut
  s'exécuter (`taskset`).
- **Cœurs hybrides** (*hybrid cores*) : cœurs performants (P) et efficaces (E)
  de microarchitectures et fréquences différentes dans un même processeur.
- **Ordonnanceur** (*scheduler*) : partie du noyau qui décide quel fil
  d'exécution tourne sur quel CPU et quand.
- **vDSO** (*virtual dynamic shared object*) : code fourni par le noyau et exécuté
  en espace utilisateur, qui permet notamment de lire l'horloge sans appel
  système complet.
- **Défaut de page mineur** (*minor page fault*) : interruption par laquelle le
  noyau associe une page déjà en mémoire à l'espace d'adressage du processus.
- **Changement de contexte involontaire** (*involuntary context switch*) : le
  processus est retiré du CPU par l'ordonnanceur alors qu'il pouvait continuer.
- **Niveau d'optimisation** (*optimization level*) : ensemble de transformations
  que le compilateur s'autorise (`-O0` à `-O3`), propre à chaque compilateur.
- **Comportement observable** (*observable behavior*) : ce que la norme oblige le
  compilateur à préserver ; la durée d'exécution n'en fait pas partie.
- **Élimination du code mort** (*dead code elimination*) : suppression d'un calcul
  dont aucun effet observable ne dépend.
- **Formule fermée** (*closed form*, *final value replacement*) : expression qui
  remplace une boucle en donnant directement sa valeur finale.
- **Vectorisation** (*vectorization*, *SIMD*) : traitement de plusieurs éléments
  par instruction à l'aide de registres larges (`xmm`, `ymm`).
- **Assembleur** (*assembly*) : forme lisible des instructions machine ; en
  syntaxe Intel, la destination est le premier opérande.
- **Unité de traduction** (*translation unit*) : fichier source compilé
  séparément ; sans *LTO*, son code est invisible aux autres unités.
- **Coût fixe par appel** (*per-call overhead*) : part de la durée d'un appel qui
  ne dépend pas du nombre d'éléments traités.
- **Exécution dans le désordre** (*out-of-order execution*) : exécution des
  instructions dès que leurs entrées sont prêtes, indépendamment de leur ordre
  dans le programme.
- **Parallélisme au niveau des instructions** (*instruction-level parallelism*) :
  progression simultanée d'instructions indépendantes.
- **Chaîne de dépendance portée par la boucle** (*loop-carried dependency chain*) :
  instructions qui attendent le résultat de l'itération précédente ; sa latence
  borne la vitesse de la boucle.
- **Latence** (*latency*, au sens microarchitectural) : nombre de cycles entre la
  disponibilité des entrées d'une instruction et celle de son résultat.
- **Prédiction de branchement** (*branch prediction*) : pari du processeur sur la
  direction d'un saut conditionnel, pour exécuter la suite par anticipation.
- **Mauvaise prédiction** (*branch misprediction*) : pari perdu ; le travail
  anticipé est jeté, pour une pénalité de l'ordre de la dizaine de ns ici.
- **Instruction conditionnelle sans branchement** (*branchless code*, `cmov`) :
  calcul des deux possibilités puis choix, sans pari ni pénalité.
- **Masque** (*mask*) : forme vectorielle d'une condition, un mot de bits par
  élément, combiné par opérations logiques.
- **Hiérarchie mémoire** (*memory hierarchy*) : registres, caches L1, L2, L3 et
  mémoire vive, du plus rapide et petit au plus lent et grand.
- **Défaut de cache** (*cache miss*) : donnée absente d'un niveau de cache, à
  chercher au niveau suivant.
- **Ligne de cache** (*cache line*) : unité de copie entre niveaux de cache,
  64 octets sur cette machine.
- **Localité** (*locality*) : tendance des accès à porter sur des données proches
  (spatiale) ou déjà utilisées (temporelle).
- **Préchargement matériel** (*hardware prefetching*) : chargement anticipé de
  lignes de cache par le processeur, quand il reconnaît un motif d'accès.
- **TLB** (*translation lookaside buffer*) : cache des traductions d'adresses
  virtuelles en adresses physiques.
- **Page géante transparente** (*transparent huge page*) : page de 2 Mio allouée
  par le noyau à la place de pages de 4 Kio ; demandée par processus avec
  `madvise(MADV_HUGEPAGE)` quand le réglage global est `madvise`.
- **Bande passante mémoire** (*memory bandwidth*) : débit de lecture ou d'écriture
  soutenu entre processeur et mémoire vive.
- **Latence d'accès** (*access latency*) : durée pour obtenir une donnée précise ;
  à distinguer du débit quand plusieurs accès se recouvrent.
- **Accès dépendants** (*pointer chasing*) : parcours où l'adresse de chaque accès
  est la valeur lue au précédent ; il empêche le recouvrement des défauts de cache.
- **Adresse virtuelle, adresse physique** (*virtual*, *physical address*) : adresse
  manipulée par le programme, et adresse réelle en mémoire vive.
- **Table des pages** (*page table*) : structure à plusieurs niveaux qui traduit les
  adresses virtuelles en adresses physiques.
- **Défaut de TLB** (*TLB miss*) : traduction absente de la TLB, qui oblige à
  parcourir la table des pages (*page walk*).
- **Page géante** (*huge page*) : page de 2 Mio, qui couvre 512 pages de 4 Kio.
- **Défaut de page** (*page fault*) : premier accès à une page virtuelle sans page
  physique ; le noyau alloue et met à zéro une page. **Mineur** (*minor*) quand
  aucun disque n'est lu.
- **Cycle de Sattolo** (*Sattolo's algorithm*) : permutation aléatoire formant un
  seul cycle qui passe par tous les éléments.

