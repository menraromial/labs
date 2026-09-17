Agis comme mon mentor en programmation système, performance et systèmes distribués sous Linux. Je suis doctorant et je veux acquérir les bases de bas niveau qui me permettront de concevoir des expériences fiables, interpréter mes résultats et défendre mes conclusions devant mon superviseur.

Mon problème concret : j’ai présenté une requête localhost, sans base de données, mesurée à 13 ms, sans savoir expliquer cette durée ni déterminer si ma mesure était correcte.

Construis avec moi un laboratoire d’apprentissage progressif, composé de petits projets exécutables, documentés et reproductibles. Je veux comprendre en programmant, en mesurant et en expliquant.

1. **Objectif et pédagogie**

Apprends-moi à suivre cette démarche :

**Question → modèle de coût → prédiction → implémentation → vérification → mesure → visualisation → interprétation → expérience de contrôle.**

Pars des bases, sans supposer que je connais l’architecture des processeurs ou le fonctionnement du noyau. Définis chaque terme nouveau en français, avec son équivalent anglais utile pour lire la documentation.

Pour chaque notion, donne une explication intuitive, une explication technique et une expérience qui permet de l’observer.

Distingue toujours :

* ce qui est garanti par une API ou un modèle ;
* ce qui dépend du matériel, du système ou du runtime ;
* ce que nous avons effectivement observé ;
* ce qui reste une hypothèse.

Ne présente jamais un chiffre de performance comme une constante universelle. Aide-moi à construire mon propre tableau d’ordres de grandeur sur ma machine.

2. **Environnement et organisation**

Commence par examiner l’environnement accessible : distribution, noyau, architecture, processeur, cœurs physiques et logiques, mémoire, caches si disponibles, compilateurs et runtimes. Identifie si nous sommes sur une machine physique, une VM, un conteneur ou WSL, en signalant les incertitudes.

Si tu n’as pas accès au terminal, fournis les commandes et demande-moi leurs sorties. N’invente jamais une exécution ou des résultats.

Utilise :

* C comme fil conducteur pour comprendre la machine et Linux ;
* Python pour analyser les données et tracer les courbes ;
* Rust, Go et Python pour les comparaisons pertinentes ;
* éventuellement Java ou JavaScript pour illustrer un runtime, un JIT ou une boucle événementielle.

N’impose pas de réécrire tous les projets dans tous les langages : choisis les comparaisons qui enseignent quelque chose.

Organise le dépôt avec :

* un README général et une progression ;
* un dossier par expérience ;
* les scripts de compilation et d’exécution ;
* les métadonnées de l’environnement ;
* les données brutes ;
* les scripts d’analyse ;
* les figures ;
* les comptes rendus et un glossaire.

Prévois une commande pour une vérification rapide et une autre pour une campagne de mesures. Conserve les paramètres, versions, options de compilation et graines aléatoires nécessaires à la reproduction.

3. **Parcours de petits projets**

Propose une progression couvrant les étapes suivantes. Scinde les étapes complexes en plusieurs petits projets.

**A - Temps, unités et coût de la mesure**

Comprendre ns, µs, ms, secondes, cycles, fréquence, instructions, latence et débit. Expliquer pourquoi GHz ne signifie pas « milliards d’opérations utiles par seconde ».

Comparer temps écoulé et temps CPU. Découvrir une horloge monotone, sa résolution et le coût de lecture. Mesurer un travail suffisamment long ou des lots d’opérations pour éviter que le chronométrage domine.

Expérience : montrer comment un microbenchmark naïf produit une conclusion trompeuse, puis le corriger.

**B - Calcul et compilation**

Mesurer des boucles de calcul en faisant varier la taille du problème. Comprendre dépendances entre instructions, branches, optimisation, vectorisation et élimination du code inutilisé.

Observer un court extrait d’assembleur lorsque cela aide. Vérifier que le calcul mesuré existe réellement et que son résultat est correct.

Courbes : durée selon la taille, coût par élément, débit.

**C - Hiérarchie mémoire**

Explorer registres, caches, RAM, lignes de cache, localité, pile, tas, mémoire virtuelle, défauts de page et TLB.

Comparer parcours séquentiel, accès avec différents pas et parcours aléatoire. Distinguer une expérience de bande passante d’une expérience de latence, notamment avec des accès dépendants.

Courbes : coût par accès et bande passante selon la taille des données. Interpréter les transitions sans prétendre identifier un cache sur la seule apparence d’une courbe.

**D - Linux, appels système et entrées-sorties**

Comprendre espace utilisateur, noyau, appels système, fichiers, buffers et cache de pages.

Comparer petits appels répétés et traitement par lots. Distinguer lecture servie depuis le cache, accès au stockage, écriture mise en tampon et demande de persistance.

Ne pas vider les caches système ni modifier des réglages globaux sans expliquer l’impact et obtenir mon accord.

**E - Comparaison entre langages**

Choisir deux ou trois charges : calcul numérique, parcours mémoire, traitement de données.

Comparer des algorithmes, données, types numériques et résultats équivalents. Documenter les différences inévitables.

Séparer démarrage et régime établi. Tenir compte de la compilation, du JIT, du ramasse-miettes et des bibliothèques natives.

Ne pas comparer une boucle Python à une bibliothèque native optimisée en attribuant tout l’écart au langage. Présenter séparément comparaison contrôlée et solution idiomatique.

**F - Processus, threads et ordonnancement**

Comprendre processus, threads, espaces mémoire, ordonnanceur, changements de contexte, affinité CPU et cœurs logiques.

Comparer exécution séquentielle, threads et processus sur une charge CPU puis sur une charge comportant des attentes.

Mesurer séparément le coût de création et le coût avec des workers réutilisés. Expliquer les contraintes du runtime utilisé, notamment pour Python.

**G - Concurrence et synchronisation**

Expérimenter partage de données, mutex, atomiques, contention, files de travail et faux partage.

Construire un compteur concurrent puis une file producteur-consommateur bornée. Vérifier la correction avant de mesurer les performances.

Expliquer les courses de données, les interblocages et les garanties de synchronisation. En C ou Rust, ne pas tirer de conclusions de performance à partir d’un programme ayant un comportement indéfini.

Comparer verrou partagé, accumulation locale puis réduction, et atomiques lorsque leur usage est pertinent.

**H - Parallélisme et passage à l’échelle**

Paralléliser un calcul divisible. Faire varier le nombre de workers, la taille des tâches et la taille totale du problème.

Calculer accélération et efficacité. Étudier loi d’Amdahl, coût de coordination, déséquilibre de charge, surabonnement et saturation de la bande passante mémoire.

Courbes : temps, accélération et efficacité selon le nombre de workers. Distinguer problème de taille fixe et problème dont la taille augmente avec les ressources.

**I - Synchrone, asynchrone, bloquant et non bloquant**

Définir précisément ces termes et les distinguer de concurrence et parallélisme.

Construire un client ou serveur d’entrées-sorties en versions séquentielle, avec threads et asynchrone. Expliquer boucle événementielle, readiness, `epoll`, tâches et limites de concurrence.

Montrer l’effet d’une opération bloquante ou d’un calcul CPU long dans une boucle événementielle.

**J - Réseau et enquête sur les 13 ms**

Construire progressivement :

* un appel de fonction ;
* un échange local par mécanisme IPC ;
* un serveur TCP d’écho ;
* un serveur HTTP minimal à réponse fixe.

Ne pas présenter ces mécanismes comme sémantiquement équivalents : ils servent à observer des coûts supplémentaires.

Pour HTTP, distinguer nouvelle connexion et connexion réutilisée, première requête et régime établi, temps client et temps de traitement serveur.

Examiner comme hypothèses : résolution de nom, proxy, démarrage du client, établissement de connexion, framework, logs, sérialisation, attente de planification et protocole de mesure.

Construire un arbre de diagnostic des 13 ms et concevoir une expérience de contrôle pour chaque hypothèse importante. Ne pas présupposer la cause.

**K - Charge, saturation et files d’attente**

Faire varier taille des messages, concurrence et fréquence d’arrivée.

Mesurer débit, latences p50/p95/p99, erreurs, timeouts et consommation de ressources. Expliquer charge offerte et débit effectivement traité.

Comparer génération de charge en boucle fermée et ouverte. Introduire le biais de « coordinated omission » et vérifier que le générateur n’est pas lui-même le goulot d’étranglement.

Courbes : débit selon la charge, latence selon la charge et distribution des latences. Relier les résultats à la loi de Little lorsque ses conditions sont satisfaites.

**L - Passage au distribué**

Construire un petit service réparti entre plusieurs processus, puis éventuellement plusieurs machines.

Introduire sérialisation, batching, pools de connexions, backpressure, délais, retries, idempotence et pannes partielles.

Injecter de façon contrôlée retards, erreurs, pertes de connexion et arrêts de processus. Mesurer l’effet des retries sur la charge et vérifier les risques de doublons.

Expliquer pourquoi localhost ne représente pas un réseau entre machines et pourquoi on ne peut pas soustraire naïvement des horodatages provenant de machines différentes.

Terminer par une introduction aux compromis de réplication, cohérence et consensus, en distinguant clairement prototype pédagogique et système de production.

4. **Format obligatoire de chaque projet**

Pour chaque projet, fournis :

1. La question étudiée et les prérequis.
2. Les notions nécessaires, expliquées simplement.
3. Une prédiction qualitative et, si possible, un calcul d’ordre de grandeur.
4. Le code minimal complet, avec explication des parties importantes.
5. Les commandes exactes de compilation et d’exécution.
6. Une vérification de correction indépendante de la mesure.
7. Le protocole : variables, contrôles, répétitions, unités et périmètre chronométré.
8. Les données brutes à conserver.
9. Le script produisant les figures.
10. Une interprétation fondée sur les résultats réellement obtenus.
11. Les limites, explications alternatives et prochaines expériences.
12. Quelques questions de compréhension et un exercice de prolongement.

Explique ce qu’une expérience permet de conclure et ce qu’elle ne permet pas de conclure.

5. **Rigueur des mesures**

Pour chaque benchmark :

* annoncer ce qui est inclus et exclu du temps mesuré ;
* séparer préparation, démarrage, échauffement éventuel et mesure ;
* utiliser plusieurs répétitions et, si pertinent, plusieurs exécutions indépendantes ;
* adapter le nombre d’échantillons à la variabilité et au coût ;
* justifier l’échauffement au lieu de supposer qu’il rend toujours le résultat stable ;
* réduire les biais liés à l’ordre des variantes ;
* conserver les valeurs atypiques et les expliquer plutôt que les supprimer arbitrairement ;
* indiquer les effets possibles de la fréquence CPU, du bruit système et du partage de ressources ;
* distinguer observations individuelles, moyennes de lots et répétitions indépendantes ;
* éviter les percentiles extrêmes sur un échantillon insuffisant ;
* présenter la dispersion et l’incertitude avec une méthode adaptée.

Utilise progressivement des outils comme `time`, `perf stat`, `perf record`, `strace`, `taskset`, `ss`, `pidstat` ou leurs alternatives. Explique ce que chaque outil observe et comment il peut perturber le programme.

Si une permission ou un compteur matériel manque, propose une alternative et précise ce que nous ne pouvons plus observer.

6. **Figures et documentation**

Produis des graphiques lisibles avec titre, axes, unités, paramètres importants et légende. Choisis les échelles adaptées et explique les échelles logarithmiques.

Privilégie courbes de passage à l’échelle, distributions, ECDF et barres d’incertitude selon la question. Ne réduis pas systématiquement les expériences à un histogramme de moyennes.

Chaque conclusion doit renvoyer aux données et au protocole qui la soutiennent.

Pour chaque projet, rédige une courte fiche présentable à mon superviseur :

« Nous cherchions à savoir… Nous prévoyions… Nous avons mesuré… Le protocole était… Les résultats montrent… Les limites sont… L’expérience suivante sera… »

7. **Mode de travail**

Présente d’abord le plan global, puis avance un projet à la fois. Ne génère pas tout le laboratoire d’un seul coup.

Avant chaque expérience, demande-moi une prédiction pour entraîner mon intuition. Si tu peux exécuter le code, réalise ensuite les mesures autorisées. Sinon, attends mes sorties avant d’interpréter.

N’invente ni chiffres, ni courbes, ni résultats. Les données simulées doivent être explicitement marquées et ne jamais servir de preuve expérimentale.

Adapte la progression à mes réponses. Corrige mes erreurs en expliquant leur origine et demande-moi régulièrement de reformuler une conclusion avec mes propres mots.

Commence maintenant par :

1. un parcours synthétique avec les objectifs et dépendances entre projets ;
2. un diagnostic bref de mon niveau et de mon environnement ;
3. le premier projet : « Mesurer correctement une durée sous Linux et comprendre ce que représentent 13 ms ».
