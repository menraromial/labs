# Laboratoire Linux : systèmes, performance et distribué

Ce dépôt sert à apprendre par la démarche suivante :

> Question → modèle de coût → prédiction → implémentation → vérification → mesure → visualisation → interprétation → expérience de contrôle

Les résultats de performance de ce dépôt décrivent **la machine et le protocole
documentés**, pas une constante universelle.

## Progression

| Étape | Projet | Objectif principal | Dépend de |
|---|---|---|---|
| A1 | Mesurer une durée | unités, horloges, coût de mesure, temps écoulé/CPU | aucun |
| A2 | Réparer un microbenchmark | lots, répétitions, dispersion, biais d'ordre | A1 |
| B1 | Calcul et compilation | optimisation, travail éliminé, assembleur | A2 |
| B2 | Dépendances et branches | ILP, vectorisation, prédiction de branche | B1 |
| C1 | Parcours mémoire | localité, lignes de cache, bande passante | A2, B1 |
| C2 | Accès dépendants | latence, caches, TLB, défauts de page | C1 |
| D1 | Appels système | espace utilisateur/noyau, batching | A2 |
| D2 | Fichiers et persistance | buffers, cache de pages, `fsync` | D1 |
| E1 | Comparaison contrôlée | C, Rust, Go et Python à travail équivalent | B1, C1 |
| E2 | Runtimes | démarrage, régime établi, JIT/GC si pertinent | E1 |
| F1 | Processus et threads | création, réutilisation, ordonnancement | B1, D1 |
| F2 | CPU contre attente | workers, affinité, contraintes Python | F1 |
| G1 | Compteur concurrent | mutex, atomiques, contention, correction | F1 |
| G2 | File bornée | producteur-consommateur, backpressure | G1 |
| G3 | Faux partage | lignes de cache et cohérence | C1, G1 |
| H1 | Passage à l'échelle | accélération, efficacité, loi d'Amdahl | F2, G1 |
| H2 | Granularité et saturation | coordination, déséquilibre, mémoire | H1 |
| I1 | Trois modèles d'I/O | séquentiel, threads, asynchrone | D1, F1 |
| I2 | Boucle événementielle | `epoll`, blocage accidentel, calcul CPU | I1 |
| J1 | Coûts locaux progressifs | fonction, IPC, TCP, HTTP | D1, I1 |
| J2 | Enquête sur les 13 ms | arbre d'hypothèses et contrôles | J1, A2 |
| K1 | Charge et files | débit, p50/p95/p99, saturation | J2, H1 |
| K2 | Générateur fiable | boucle ouverte/fermée, coordinated omission | K1 |
| L1 | Service multiprocessus | sérialisation, pools, délais, retries | G2, J2 |
| L2 | Pannes partielles | idempotence, backpressure, doublons | L1, K2 |
| L3 | Réplication | cohérence et consensus, introduction | L2 |

Le chemin principal est `A → B/C/D → F/G/H → I/J → K → L`. La comparaison
entre langages (`E`) réutilise des charges déjà comprises afin de ne pas confondre
algorithme, bibliothèque et langage.

## État actuel

- [x] Environnement initial examiné et consigné.
- [x] Projet A1 : hypothèses formulées avant la mesure.
- [x] Projet A1 : implémentation, vérification et première campagne.
- [x] Projet A1 : figure, interprétation et fiche superviseur.
- [ ] Projet A1 : application au programme localhost d'origine.
- [x] Projet A2 : prédictions, contrôles A/A et positif, campagne répliquée.
- [x] Projet A2 : contrôle exploratoire du premier passage et des cœurs hybrides.
- [x] Projet A2 : figures, interprétation et fiche superviseur.
- [x] Projet B1 : analyse statique de l'assembleur et prédictions avant mesure.
- [x] Projet B1 : campagne GCC et Clang, -O0 à -O3, contrôles A/A et positif.
- [x] Projet B1 : figures, interprétation et fiche superviseur.
- [x] Projet B2 : analyse statique, prédictions, campagne sur 6 binaires.
- [x] Projet B2 : dépendances, branchements, petites boucles, fiche superviseur.
- [x] Projet C1 : prédictions et contrôle d'attribution fixés avant la campagne.
- [x] Projet C1 : campagne sur cœurs P, E et LP-E, interprétation, fiche superviseur.

Voir [le diagnostic initial](docs/environment-observed.md),
[le projet A1](experiments/01-time/README.md),
[le projet A2](experiments/02-microbenchmark/README.md),
[le projet B1](experiments/03-compilation/README.md),
[le projet B2](experiments/04-dependencies-branches/README.md) et
[le projet C1](experiments/05-memory-traversal/README.md).

## Structure cible (créée progressivement)

Chaque expérience possédera son code, ses scripts, ses données brutes, ses
figures et son compte rendu. Nous ne créons pas les expériences suivantes avant
d'en avoir besoin. Le glossaire commun se trouve dans
[`docs/glossary.md`](docs/glossary.md).

La typographie suit le [`guide de style`](docs/style-guide.md). Les figures
suivent les [règles de style des figures](STYLE_FIGURES.md), appliquées par
le module partagé [`tools/figstyle.py`](tools/figstyle.py).

## Site du laboratoire

Le dossier [`site/`](site/README.md) contient un site Docusaurus qui publie la
progression, les comptes rendus, les fiches superviseur, les figures, le code et
l'inventaire des données. Il est régénéré à partir de `experiments/` à chaque
`npm start` ou `npm run build` : une nouvelle expérience n'a rien à déclarer.
