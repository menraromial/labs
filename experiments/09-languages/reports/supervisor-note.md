# Fiche superviseur - comparaison entre langages

**Nous cherchions à savoir** ce que coûte le même calcul, à travail strictement
équivalent (mêmes données, même algorithme, mêmes types, même résultat), en C, Rust,
Go et Python, et ce que changent l'écriture idiomatique de chaque langage et le recours
à NumPy. Le démarrage des programmes était mesuré à part.

**Nous prévoyions**, après lecture de l'assembleur : C, Rust et Go à 15 % près les uns
des autres, les vérifications de bornes coûtant au plus 30 % (Rust) à 50 % (Go) dans la table de
hachage ;
Python contrôlé 60 à 250 fois plus lent que C pour la chaîne entière ; aucun gain des
itérateurs en compilé ; des tables de hachage générales à 10 à 30 ns par élément ;
`np.dot` 2 à 8 fois plus rapide que la boucle C stricte ; un démarrage de 10 à 40 ms pour
Python et de 50 à 200 ms avec NumPy.

**Nous avons mesuré** C, Rust et Go à 4 % près sur les trois charges (1,84 à 1,91 ns
par élément pour la chaîne entière, 1,48 à 1,51 ns pour le produit scalaire, 3,45 à
3,59 ns pour la table). GCC `-O3` est 12 % plus lent que `-O2` sur le produit scalaire.
Python contrôlé coûte 30 (flottants) à 78 fois (table) C. Itérateurs et boucles
indexées coûtent pareil en Rust et en Go ; en Python, les fonctions natives
(`math.sumprod`, `collections.Counter`) divisent le coût par 2,6 à 3,7. Les tables de
hachage de Rust et de Go coûtent 4,7 et 5,6 fois une table dédiée. NumPy est 45 à
100 fois plus rapide que la boucle Python et 1,2 à 1,5 fois plus rapide que la boucle C,
en faisant un travail différent (ordre des additions, indexation directe). Aucune
collecte du ramasse-miettes pendant les mesures. Démarrage : 0,6 à 1,5 ms pour les
compilés, 19,8 ms pour Python, 99,7 ms avec NumPy ; mémoire 67 Mio en C, 585 Mio en
Python. Trois prédictions de valeur absolue sont réfutées (C plus lent que prévu sur la
chaîne, Python plus rapide que prévu sur `dot` et la table, `Counter` plus lent), ainsi
que l'ampleur du gain de `np.dot` et le contrôle A/A des versions compilées.

**Le protocole était** un fichier de $2^{22}$ entiers commun, trois charges traduites
à l'identique dans chaque langage et vérifiées pour chaque échantillon contre un calcul
Python indépendant (résultats identiques au bit près, sauf `math.sumprod` et `np.dot`) ;
5 versions (GCC `-O2` et `-O3`, `rustc -C opt-level=3`, Go 1.26, CPython 3.14 avec
NumPy) ; 10 processus indépendants par version, épinglés sur un cœur P, dans un ordre
aléatoire fixé ; 11 tours dont le premier jeté ; collectes forcées avant chaque
échantillon ; 50 démarrages de chaque commande.

**Les résultats montrent** qu'à travail équivalent, le langage compilé ne change rien
de mesurable ici, et que les écarts spectaculaires viennent de l'interprétation ou de
changements d'algorithme et de bibliothèque. Une comparaison « Python contre C » par
NumPy compare des bibliothèques ; une comparaison par tables de hachage idiomatiques
compare des structures de données.

**Les limites sont** trois petites charges, une version de chaque chaîne de compilation,
des options par défaut, un seul cœur, et une campagne commencée à une charge moyenne de
3,54 : les A/A des versions compilées sortent de ±3 % dans certains processus, et les
écarts de moins de 5 % ne sont pas interprétés.

**L'expérience suivante sera** E2 (démarrage détaillé, JIT, ramasse-miettes sous
pression). Pour les 13 ms : le seul démarrage de l'interpréteur Python (19,8 ms) dépasse
13 ms ; si la requête a été mesurée par un client Python lancé pour l'occasion, le
démarrage peut dominer la mesure, hypothèse prioritaire pour J2.
