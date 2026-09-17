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
- **Espace utilisateur, espace noyau** (*user space*, *kernel space*) : exécution
  avec droits restreints, et exécution du noyau avec tous les droits.
- **Appel système** (*system call*) : demande explicite d'un service au noyau, avec
  changement de mode du processeur à l'entrée et à la sortie.
- **Atténuation** (*mitigation*) : protection du noyau contre une vulnérabilité
  matérielle, souvent au prix d'un surcoût à l'entrée ou à la sortie du noyau.
- **Descripteur de fichier** (*file descriptor*) : entier désignant un fichier ouvert
  par le processus.
- **Traitement par lots** (*batching*) : regrouper en un appel ce qui aurait demandé
  plusieurs appels.
- **Tampon** (*buffer*) : zone où les données s'accumulent avant d'être transmises
  en une fois.
- **Temps utilisateur, temps système** (*user time*, *system time*) : temps CPU
  passé dans le programme ou dans le noyau pour son compte ; sous Linux, réparti
  par échantillonnage au tick.
- **Cache de pages** (*page cache*) : mémoire où le noyau garde le contenu des
  fichiers ; une lecture qui y trouve ses données ne touche pas le disque.
- **Lecture anticipée** (*readahead*) : lecture par le noyau de la suite d'un fichier
  lu séquentiellement, avant qu'elle soit demandée.
- **Entrée-sortie directe** (*direct I/O*, `O_DIRECT`) : lecture ou écriture qui
  contourne le cache de pages.
- **Page sale** (*dirty page*) : page du cache modifiée, pas encore écrite sur le
  disque ; le noyau l'écrit plus tard (*writeback*).
- **Persistance** (*durability*) : garantie que des données écrites survivent à une
  coupure ; demandée par `fsync`, `fdatasync` ou `O_DSYNC`, jamais vérifiable sans
  couper l'alimentation.
- **Journal** (*journal*, *jbd2*) : zone où ext4 écrit d'abord ses modifications de
  métadonnées, validées par transactions (*commit*).
- **Vidage du cache du disque** (*flush*) et **FUA** (*force unit access*) : demande
  au disque de rendre persistantes les écritures gardées dans sa mémoire volatile,
  pour toutes ou pour une seule écriture.
- **Folio** (*folio*) : unité de gestion du cache de pages, d'une ou de plusieurs
  pages contiguës.
- **Regroupement des validations** (*group commit*) : une seule demande de
  persistance pour plusieurs écritures, qui en partage le coût fixe.
- **Centile** (*percentile*) : le 95ᵉ centile d'une série est la valeur sous laquelle
  se trouvent 95 % des observations.
- **Fonction de répartition empirique** (*ECDF*) : pour chaque valeur, la fraction des
  observations qui lui sont inférieures ou égales.
- **Écart interquartile relatif** (*relative interquartile range*) : écart entre les
  75ᵉ et 25ᵉ centiles, divisé par la médiane.
- **Corrélation de rang de Spearman** (*Spearman rank correlation*) : corrélation
  entre les rangs de deux séries, de -1 à 1.
- **Coefficient de détermination** (*coefficient of determination*, $R^2$) : part de la
  variation expliquée par un ajustement ; 1 pour un ajustement parfait.
- **Déroulage de boucle** (*loop unrolling*) : le compilateur écrit plusieurs itérations
  par tour de boucle.
- **Demi-octave** : facteur $\sqrt{2}$ entre deux tailles successives.
- **Compilation anticipée** (*ahead-of-time compilation*) : traduction du programme en
  code machine avant son exécution (C, Rust, Go).
- **Interpréteur** (*interpreter*) : programme qui exécute un code intermédiaire
  (*bytecode*) instruction par instruction, comme CPython.
- **Compilation à la volée** (*just-in-time compilation*, JIT) : traduction en code
  machine pendant l'exécution, des parties souvent exécutées.
- **Ramasse-miettes** (*garbage collector*) : récupération automatique de la mémoire qui
  n'est plus utilisée.
- **Vérification de bornes** (*bounds check*) : test qu'un indice est dans le tableau
  avant d'y accéder ; le compilateur peut l'éliminer quand il prouve qu'elle réussit.
- **Bibliothèque native** (*native library*) : code compilé appelé depuis un langage
  interprété (NumPy, OpenBLAS).
- **Traduction contrôlée, écriture idiomatique** (*controlled translation*, *idiomatic
  code*) : même algorithme écrit de la même façon dans chaque langage, ou écrit comme
  le ferait un habitué de chaque langage.
- **Durée de démarrage** (*startup time*) : du lancement d'un programme au moment où il
  peut travailler ; ici mesurée sur un programme qui se termine aussitôt.
- **Liaison dynamique** (*dynamic linking*) : chargement et raccordement des bibliothèques
  partagées au lancement d'un programme ; un exécutable **statique** les contient déjà.
- **Remplacement sur pile** (*on-stack replacement*, OSR) : passage d'une boucle en cours
  d'exécution du code interprété au code compilé par le JIT.
- **Désoptimisation** (*deoptimization*) : retour d'un code compilé par le JIT vers un code
  moins optimisé, quand une hypothèse du compilateur cesse d'être vraie.
- **Ramasse-miettes générationnel** (*generational garbage collector*) : collecteur qui
  collecte souvent une zone d'objets jeunes et plus rarement les survivants promus.
- **Pause** (*stop-the-world pause*) : période où le programme est arrêté par le
  ramasse-miettes.
- **Surcoût d'échauffement** (*warm-up overhead*) : temps perdu par rapport au régime
  établi pendant qu'un environnement d'exécution optimise le code.
