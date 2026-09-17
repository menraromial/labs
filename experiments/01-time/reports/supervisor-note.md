# Fiche superviseur - mesurer correctement une durée

**Nous cherchions à savoir** ce que mesure une durée écoulée et si le coût d'une
lecture d'horloge pouvait expliquer à lui seul une observation de 13 ms.

**Nous prévoyions** des lectures d'horloge de l'ordre de dizaines de ns sur cet
environnement, une attente de 100 ms consommant peu de temps CPU, et une charge
active présentant des temps CPU et écoulé proches.

**Nous avons mesuré** une médiane de 28 ns entre deux lectures consécutives et
27 ns par lecture dans les lots. Une attente demandée de 100 ms a eu une médiane
de 100,086 ms écoulées pour 0,027 ms de CPU. La charge visant 50 ms de CPU a eu des
médianes de 50,003 ms écoulées et 50,002 ms de CPU. Une valeur atypique de
8,244 µs apparaît parmi les 50 000 paires et reste dans les données.

**Le protocole était** une compilation C avec GCC et `-O2`, 50 000 mesures
unitaires, 50 lots de 10 000 lectures et 50 répétitions des charges. Nous avons
utilisé `CLOCK_MONOTONIC` et `CLOCK_PROCESS_CPUTIME_ID`. L'ordre attente/calcul
alternait avec la graine 20260916. Les données brutes et l'environnement sont
conservés dans le dépôt.

**Les résultats montrent** que temps écoulé et temps CPU sont distincts et qu'une
opération très courte doit être mesurée par lots. Sur cet environnement, une
simple lecture de l'horloge ne suffit pas à expliquer 13 ms.

**Les limites sont** l'absence d'isolation CPU, une seule campagne indépendante,
une virtualisation/isolation imparfaitement identifiée et surtout l'absence du
client et du serveur HTTP originaux dans cette expérience.

**L'expérience suivante sera** d'instrumenter séparément le client, la connexion
et le traitement serveur de la requête localhost, puis de comparer première
connexion et connexion réutilisée.
