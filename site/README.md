# Site du laboratoire

Site statique [Docusaurus](https://docusaurus.io/) qui publie les comptes rendus,
fiches superviseur, figures, code et inventaires de données du laboratoire.

**Aucune page n'est écrite à la main dans `docs/`** : tout y est régénéré à partir
du dépôt par [`scripts/sync-content.mjs`](scripts/sync-content.mjs), avant chaque
`start` et chaque `build`. Une nouvelle expérience apparaît donc sur le site dès
qu'elle existe dans `experiments/`.

## Commandes

```sh
cd site
npm install          # une seule fois
npm start            # serveur local, resynchronise à chaque modification du dépôt
npm run build        # site statique dans site/build/
npm run serve        # sert site/build/ localement
npm run sync         # régénère seulement docs/ (utile pour inspecter le résultat)
```

Pour vérifier le rendu d'une expérience sans toucher au dépôt, générer le site à
partir d'une copie : `LAB_ROOT=/chemin/vers/copie npm run build`, puis relancer
`npm run build` sans la variable.

Pour une publication sous un sous-chemin (GitHub Pages par exemple) :

```sh
SITE_URL=https://utilisateur.github.io BASE_URL=/Labs/ npm run build
```

## Ce qui est publié automatiquement

| Source dans le dépôt | Page du site |
|---|---|
| `README.md` | Progression (les codes du tableau deviennent des liens) |
| `experiments/NN-nom/README.md` | Compte rendu de l'expérience |
| `experiments/NN-nom/reports/supervisor-note.md` | Fiche superviseur |
| `experiments/NN-nom/{src,*.py,*.sh,Makefile}` | Code source affiché |
| `experiments/NN-nom/figures/*.png` et `*.pdf` | Figures légendées, PDF téléchargeable |
| `experiments/NN-nom/reports/**` | Rapports calculés téléchargeables |
| `experiments/NN-nom/data/` | Inventaire (fichiers < 512 Kio téléchargeables) |
| `docs/*.md`, `STYLE_FIGURES.md` | Méthode et références |
| `tools/*` | Outils partagés |

`build/` et `__pycache__/` sont ignorés ; `promt.md` n'est pas publié.

## Conventions à respecter dans une nouvelle expérience

Le script ne demande aucune configuration ; il s'appuie sur les conventions déjà
suivies de A1 à C1 :

1. Dossier `experiments/NN-nom-court/` (le numéro fixe l'ordre) contenant un `README.md`.
2. Première ligne : `# C2 - Titre court : précisions`. Le code (`C2`) relie la page
   au tableau de progression et à l'état d'avancement (`- [x] Projet C2 : ...`)
   du README racine ; le titre court (avant « : ») sert dans la barre latérale.
3. Un paragraphe `**Question :** ...` : il devient la description de la page et le
   résumé de la carte d'accueil.
4. Liens relatifs habituels : `[B1](../03-compilation/README.md)`,
   ``[`src/x.c`](src/x.c)``, ``[`figures/campaign-x.pdf`](figures/campaign-x.pdf)``.
   Un lien vers une figure PDF dont le PNG existe affiche la figure, avec pour
   légende le texte de l'élément de liste qui la cite.
5. État affiché : « Campagne réalisée » si `data/campaign` existe, « Mise au
   point » si seuls `data/quick` ou `data/check` existent, sinon « Protocole en
   préparation ».

Un lien vers un fichier absent est signalé par `[sync] attention : ...` et
remplacé par son texte ; il ne bloque pas la publication.

## Rendu

- Markdown lu en CommonMark (`format: 'detect'`) : `<`, `{` et l'assembleur
  s'affichent sans échappement.
- Formules KaTeX : `$\frac{T_1}{T_p}$` en ligne, `$$...$$` en bloc. Un `$` isolé
  dans le texte courant doit donc être écrit dans du code (`` `$HOME` ``).
- Légendes des figures : tirées du texte qui cite la figure ; leurs formules `$...$`
  sont rendues par KaTeX (`src/plugins/remark-figure.js`).
- Diagrammes Mermaid : bloc de code ` ```mermaid `.
- Recherche locale en français, sans service externe.
