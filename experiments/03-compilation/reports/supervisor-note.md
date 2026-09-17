# Fiche superviseur - calcul et compilation

**Nous cherchions à savoir** si chronométrer une boucle C mesure le calcul écrit
dans le source, et comment le compilateur et le niveau d'optimisation changent le
travail exécuté.

**Nous prévoyions**, après lecture de l'assembleur et avant toute mesure, qu'une
somme calculée puis ignorée disparaîtrait chez GCC à -O2 et -O3 et chez Clang dès
-O1, que Clang remplacerait la somme des indices par une formule, que la pente du
coût par élément selon la taille révélerait ces cas, qu'une boucle scalaire
optimisée coûterait 0,2 à 0,4 ns par élément et -O0 trois à huit fois plus.

**Nous avons mesuré** un accord de 40 sur 40 entre la pente du coût et la présence
d'une boucle dans l'assembleur. Une fonction éliminée coûte environ 1,6 ns par
appel ; mesurée sur un seul appel, elle affiche le seul coût du chronomètre et un
« débit » d'environ 90 000 milliards d'éléments par seconde. Pour la même somme, à
512 Kio : 3,06 ns par élément avec GCC -O0, 1,02 ns avec Clang -O0, 0,415 ns pour
les boucles scalaires optimisées des deux compilateurs, 0,204 ns avec GCC -O3
(SSE2, 2 voies) et 0,140 ns avec Clang -O2 (4 voies), soit un facteur 22 entre
extrêmes. À 32 Mio, tous les binaires optimisés convergent vers 0,71 à 0,77 ns
par élément. Les contrôles A/A (0,989 à 1,014) et positif (1,953 à 2,050) sont
respectés dans les 120 processus.

**Le protocole était** 8 binaires (GCC 15.2 et Clang 21.1, -O0 à -O3) partageant
un harnais compilé une fois par GCC -O2 ; 15 processus indépendants par binaire,
dans un ordre aléatoire fixé, épinglés sur un cœur P ; 16 tours par processus,
dont le premier jeté, avec les 45 couples (mesure, taille) dans un ordre tiré à
chaque tour ; 9 tailles de 64 à 4 194 304 éléments. Chaque résultat a été
vérifié, identique pour tous les binaires et recalculé en Python.

**Les résultats montrent** qu'un temps mesuré n'a de sens qu'avec le binaire qui
l'a produit : le compilateur peut supprimer, remplacer, alléger ou vectoriser une
boucle, et un résultat correct ne prouve pas que la boucle a tourné. Lire
l'assembleur et vérifier la forme de la courbe selon la taille suffisent ici à
détecter ces transformations. « -O0 » n'est pas une référence commune : GCC -O0
est trois fois plus lent que Clang -O0.

**Les limites sont** l'absence de compteurs matériels, qui empêche de raisonner
en cycles ; un CPU non réservé ; quatre noyaux très simples ; un seul processeur.
La fréquence `scaling_cur_freq` s'est révélée inutilisable comme observable
(2,4 à 2,5 GHz relevés, alors qu'une itération de boucle vide dure 0,203 ns), et
l'hypothèse de fréquence laissée ouverte par A2 reste donc non testée.

**L'expérience suivante sera** B2 (dépendances, vectorisation, prédiction de
branchement), avec un test de l'hypothèse selon laquelle le coût fixe des boucles
scalaires, environ 12 ns par appel, vient d'une sortie de boucle mal prédite.
Pour les 13 ms, B1 ajoute une vérification préalable : le mode de compilation du
client et du serveur d'origine.
