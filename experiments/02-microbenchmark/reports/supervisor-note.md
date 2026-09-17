# Fiche superviseur - réparer un microbenchmark naïf

**Nous cherchions à savoir** si un microbenchmark naïf pouvait produire une
conclusion fausse sur cette machine, et quelles corrections (lots, répétitions,
ordre aléatoire, échauffement, processus indépendants) rendaient une comparaison
défendable.

**Nous prévoyions** un coût apparent dominé par le chronomètre pour une seule
opération, un rapport naïf entre un travail double et un travail simple écrasé
vers 1,1 à 1,4, un biais contre la première variante mesurée, et un protocole
entrelacé retrouvant un rapport A/A (une fonction comparée à elle-même) de 1 et un
rapport de 2 pour le travail double. Nous prévoyions aussi qu'un échauffement de 10 tours suffirait.

**Nous avons mesuré** un coût fixe de chronométrage par échantillon (deux lectures
d'horloge et l'appel mesuré) de $H \approx 30$ ns (IC 95 % de 29,4 à 31,3) et un coût par opération au plateau de 4,51 ns sur cœur P et
5,51 ns sur cœur E. Le protocole naïf a donné, dans 30 processus sur 30, un rapport A/A
médian de 0,21 : une fonction y paraît cinq fois plus lente qu'elle-même. Le
travail double y paraît 2,5 fois plus rapide que le travail simple (rapport
0,40). Avec des lots entrelacés dans un ordre aléatoire, le rapport A/A vaut
1,000 (étendue 0,976 à 1,015) et le rapport du travail double 2,000. Un contrôle
exploratoire attribue le biais naïf au premier passage dans l'horloge (environ
80 ns) et dans le code (environ 30 ns) : jeter une mesure complète ramène le
rapport du travail double à 1,10, la valeur prédite. Enfin, 26 processus sur 30
ont démarré sur un cœur E et n'ont rejoint un cœur P qu'après 10 ms médianes de
calcul (maximum 35 ms).

**Le protocole était** une compilation C17 avec GCC `-O2` ; 155 processus
indépendants exécutés dans un ordre aléatoire fixé (graine 20260916) : 20 pour
l'amortissement (tailles 1 à 32 768), 30 par protocole naïf, lot unique et lots
entrelacés (100 tours, ordre des variantes tiré à chaque tour), 15 par cœur
épinglé P, E et LP-E. Le contrôle d'amorçage a porté sur 120 processus. Les
calculs ont été rejoués en Python pour prouver que le travail chronométré avait
lieu. La campagne complète a été répliquée ; tous les résultats principaux se
reproduisent.

**Les résultats montrent** qu'une opération de quelques ns mesurée isolément
donne une conclusion fausse en amplitude et en sens, de façon reproductible. Le
biais d'ordre vient ici du premier passage dans l'horloge et le code, et la
variabilité entre processus vient surtout du type de cœur. Une comparaison
relative, entrelacée et répétée sur des processus indépendants reste juste
même lorsque le coût absolu varie d'un facteur 2,2 entre cœurs.

**Les limites sont** une seule machine, l'absence de compteurs matériels
(`perf_event_paranoid=4`), et le caractère exploratoire du contrôle d'amorçage
et de la séparation par cœur, décidés après la première campagne. L'origine de
deux niveaux de coût discrets sur cœur P (4,51 et 3,61 ns) n'est pas établie ;
deux états de fréquence sont une hypothèse. Notre échauffement déclaré de
10 tours était insuffisant : le mécanisme était un changement de cœur, pas une
montée progressive.

**L'expérience suivante sera** B1 (calcul et compilation) avec ce protocole :
processus indépendants, lots entrelacés, mesure jetée, type de cœur enregistré ou
épinglage explicite, contrôles A/A et positif. Pour l'enquête sur les 13 ms,
A2 ajoute deux hypothèses à tester : un client neuf paie des premiers passages à
froid et peut s'exécuter plusieurs millisecondes sur un cœur E.
