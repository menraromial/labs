#!/usr/bin/env node
// Génère le contenu du site à partir du dépôt du laboratoire.
//
// Sources (jamais modifiées) :
//   ../README.md                      -> docs/progression.md
//   ../docs/*.md, ../STYLE_FIGURES.md -> docs/methode/*.md
//   ../tools/*                        -> docs/methode/outils.md
//   ../experiments/NN-nom/            -> docs/experiences/NN-nom/
//        README.md                    -> index.md (compte rendu en 12 points)
//        reports/supervisor-note.md   -> fiche-superviseur.md (si présente)
//        src, scripts, figures, ...   -> artefacts.md + assets/
//
// Toute expérience ajoutée sous experiments/ avec un README.md est publiée
// sans autre intervention. Le dossier docs/ du site est entièrement généré.
//
// Usage :
//   node scripts/sync-content.mjs                         synchronise une fois
//   node scripts/sync-content.mjs --watch -- <commande>   synchronise, lance la
//        commande (serveur de développement) et resynchronise à chaque changement

import fs from 'node:fs';
import path from 'node:path';
import {execFileSync, spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const SITE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
// LAB_ROOT permet de générer le site à partir d'une autre copie du dépôt (tests).
const ROOT = path.resolve(process.env.LAB_ROOT || path.join(SITE, '..'));
const EXPERIMENTS = path.join(ROOT, 'experiments');
const OUT_DOCS = path.join(SITE, 'docs');
const OUT_DATA = path.join(SITE, 'src', 'data');
const OUT_STATIC = path.join(SITE, 'static', 'generated');

const IGNORED_DIRS = new Set(['build', '__pycache__', 'node_modules', '.git']);
const CODE_LANGUAGES = {
  '.c': 'c', '.h': 'c', '.cc': 'cpp', '.cpp': 'cpp', '.hpp': 'cpp',
  '.py': 'python', '.sh': 'bash', '.rs': 'rust', '.go': 'go',
  '.java': 'java', '.js': 'javascript', '.mjs': 'javascript', '.ts': 'typescript',
  '.toml': 'toml', '.yaml': 'yaml', '.yml': 'yaml', '.json': 'json', '.s': 'text',
};
const CODE_NAMES = {Makefile: 'makefile', 'Cargo.toml': 'toml', 'go.mod': 'go'};
const MAX_EMBEDDED_CODE = 256 * 1024;
const MAX_COPIED_DATA = 512 * 1024;
const MONTHS = new Intl.DateTimeFormat('fr-FR', {day: 'numeric', month: 'long', year: 'numeric'});

// ---------------------------------------------------------------------------
// Écriture incrémentale : seuls les fichiers modifiés sont réécrits, et les
// fichiers générés qui n'ont plus de source sont supprimés. Le serveur de
// développement ne recharge ainsi que ce qui a changé.

const generated = new Set();
const warnings = [];

function writeText(file, content) {
  generated.add(file);
  if (fs.existsSync(file) && fs.readFileSync(file, 'utf8') === content) return;
  fs.mkdirSync(path.dirname(file), {recursive: true});
  fs.writeFileSync(file, content);
}

function copyFile(src, dest) {
  generated.add(dest);
  if (fs.existsSync(dest)) {
    const a = fs.statSync(src);
    const b = fs.statSync(dest);
    if (a.size === b.size && Math.floor(b.mtimeMs) >= Math.floor(a.mtimeMs)) return;
  }
  fs.mkdirSync(path.dirname(dest), {recursive: true});
  fs.copyFileSync(src, dest);
  const {atime, mtime} = fs.statSync(src);
  fs.utimesSync(dest, atime, mtime);
}

function pruneStale(dir) {
  if (!fs.existsSync(dir)) return;
  for (const entry of fs.readdirSync(dir, {withFileTypes: true})) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      pruneStale(full);
      if (fs.readdirSync(full).length === 0) fs.rmdirSync(full);
    } else if (!generated.has(full)) {
      fs.unlinkSync(full);
    }
  }
}

// ---------------------------------------------------------------------------
// Utilitaires Markdown

const yaml = (value) => JSON.stringify(value);

function anchor(text) {
  return text
    .normalize('NFD').replace(/[̀-ͯ]/g, '')
    .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

/** Retire la syntaxe Markdown en ligne pour obtenir un texte brut. */
function plain(markdown) {
  return markdown
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/`([^`]*)`/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/(^|[\s(])\*([^*]+)\*/g, '$1$2')
    .replace(/\s+/g, ' ')
    .trim();
}

function fence(content) {
  const longest = Math.max(2, ...(content.match(/`{3,}/g) || []).map((m) => m.length));
  return '`'.repeat(longest + 1);
}

function humanSize(bytes) {
  const units = ['octets', 'Kio', 'Mio', 'Gio'];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  const digits = unit === 0 || value >= 100 ? 0 : 1;
  return `${value.toFixed(digits).replace('.', ',')} ${units[unit]}`;
}

function isText(file) {
  const buffer = fs.readFileSync(file);
  return !buffer.subarray(0, 8000).includes(0);
}

function walk(dir, base = dir) {
  if (!fs.existsSync(dir)) return [];
  const out = [];
  for (const entry of fs.readdirSync(dir, {withFileTypes: true}).sort((a, b) => a.name.localeCompare(b.name))) {
    if (entry.name.startsWith('.') || IGNORED_DIRS.has(entry.name)) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walk(full, base));
    else out.push(path.relative(base, full));
  }
  return out;
}

function dirStats(dir) {
  const files = walk(dir);
  const size = files.reduce((sum, f) => sum + fs.statSync(path.join(dir, f)).size, 0);
  return {count: files.length, size};
}

/** Sépare le titre de niveau 1 du reste du document. */
function splitTitle(markdown) {
  const lines = markdown.split('\n');
  const index = lines.findIndex((line) => /^#\s+/.test(line));
  if (index === -1) return {title: null, body: markdown};
  const title = lines[index].replace(/^#\s+/, '').trim();
  lines.splice(index, 1);
  while (lines[index] !== undefined && lines[index].trim() === '' && index === 0) lines.splice(index, 1);
  return {title, body: lines.join('\n').replace(/^\s*\n/, '')};
}

// ---------------------------------------------------------------------------
// Découverte du dépôt

/**
 * Date de dernière modification d'un fichier : celle du dernier commit s'il est
 * suivi par Git et inchangé (un clone ou une intégration continue donnerait sinon
 * la date du clone), la date du système de fichiers dans les autres cas.
 */
function lastModified(file) {
  const git = (...args) => execFileSync('git', args, {cwd: ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore']}).trim();
  try {
    if (git('status', '--porcelain', '--', file) === '') {
      const date = git('log', '-1', '--format=%cI', '--', file);
      if (date) return new Date(date);
    }
  } catch {
    // Pas de dépôt Git ou Git absent : repli sur la date du fichier.
  }
  return fs.statSync(file).mtime;
}

function discoverExperiments() {
  if (!fs.existsSync(EXPERIMENTS)) return [];
  return fs.readdirSync(EXPERIMENTS, {withFileTypes: true})
    .filter((e) => e.isDirectory() && /^\d+[-_]/.test(e.name))
    .filter((e) => fs.existsSync(path.join(EXPERIMENTS, e.name, 'README.md')))
    .map((e) => e.name)
    .sort((a, b) => parseInt(a, 10) - parseInt(b, 10) || a.localeCompare(b))
    .map((slug) => describeExperiment(slug));
}

function describeExperiment(slug) {
  const dir = path.join(EXPERIMENTS, slug);
  const readme = fs.readFileSync(path.join(dir, 'README.md'), 'utf8');
  const {title: rawTitle} = splitTitle(readme);
  const heading = rawTitle || slug;
  const match = heading.match(/^([A-Z]+\d+[a-z]?)\s+-\s+(.*)$/);
  const code = match ? match[1] : slug.replace(/^\d+[-_]/, '');
  const fullTitle = match ? match[2] : heading;
  const shortTitle = fullTitle.split(/\s+:\s+/)[0];

  // Question : paragraphe commençant par « **Question :** », sinon premier paragraphe.
  const paragraphs = readme.split(/\n\s*\n/).map((p) => p.trim());
  const questionParagraph = paragraphs.find((p) => /^\*\*Question\s*:?\s*\*\*/.test(p))
    || paragraphs.find((p) => p && !p.startsWith('#')) || '';
  const question = plain(questionParagraph.replace(/^\*\*Question\s*:?\s*\*\*\s*:?\s*/, ''));
  const questionText = question.charAt(0).toLocaleUpperCase('fr-FR') + question.slice(1);

  const has = (rel) => fs.existsSync(path.join(dir, rel));
  const status = has('data/campaign') || has('data/campaign.csv')
    ? 'campagne'
    : has('data/quick') || has('data/quick.csv') || has('data/check')
      ? 'mise-au-point'
      : 'protocole';

  const figures = walk(path.join(dir, 'figures')).filter((f) => f.endsWith('.png'));
  const linkedFigures = [...readme.matchAll(/\]\((figures\/[^)\s]+)\)/g)]
    .map((m) => m[1].replace(/\.pdf$/, '.png').replace(/^figures\//, ''))
    .filter((f) => figures.includes(f));
  const thumbnail = linkedFigures[0]
    || figures.find((f) => f.startsWith('campaign'))
    || figures[0] || null;

  const sections = [...readme.matchAll(/^##\s+(.+)$/gm)].map((m) => m[1].trim());

  return {
    slug, dir, code, heading, fullTitle, shortTitle, question: questionText, status, sections,
    number: parseInt(slug, 10),
    hasSupervisorNote: has('reports/supervisor-note.md'),
    figures, thumbnail,
    updated: lastModified(path.join(dir, 'README.md')),
  };
}

function discoverMethodDocs() {
  const docs = [];
  const add = (source, id, position) => {
    if (!fs.existsSync(source)) return;
    const {title} = splitTitle(fs.readFileSync(source, 'utf8'));
    docs.push({source, id, title: title || id, position});
  };
  add(path.join(ROOT, 'docs', 'glossary.md'), 'glossaire', 1);
  add(path.join(ROOT, 'docs', 'environment-observed.md'), 'environnement', 2);
  add(path.join(ROOT, 'STYLE_FIGURES.md'), 'style-figures', 3);
  add(path.join(ROOT, 'docs', 'style-guide.md'), 'guide-typographique', 4);
  // Tout autre document ajouté plus tard dans docs/ est publié tel quel.
  const known = new Set(docs.map((d) => d.source));
  const extra = fs.existsSync(path.join(ROOT, 'docs'))
    ? fs.readdirSync(path.join(ROOT, 'docs')).filter((f) => f.endsWith('.md')).sort()
    : [];
  for (const file of extra) {
    const source = path.join(ROOT, 'docs', file);
    if (!known.has(source)) add(source, anchor(file.replace(/\.md$/, '')), 10 + docs.length);
  }
  return docs;
}

/** Lit l'état d'avancement et le tableau de progression du README racine. */
function readProgression() {
  const file = path.join(ROOT, 'README.md');
  if (!fs.existsSync(file)) return {steps: [], checklist: {}};
  const text = fs.readFileSync(file, 'utf8');
  const steps = [];
  for (const line of text.split('\n')) {
    const cells = line.split('|').slice(1, -1).map((c) => c.trim());
    if (cells.length >= 3 && /^[A-Z]\d+$/.test(cells[0])) {
      steps.push({code: cells[0], project: cells[1], goal: plain(cells[2]), dependsOn: plain(cells[3] || '')});
    }
  }
  const checklist = {};
  for (const m of text.matchAll(/^\s*-\s+\[([ xX])\]\s+Projet\s+([A-Z]\d+)\b/gm)) {
    const entry = (checklist[m[2]] ||= {done: 0, total: 0});
    entry.total += 1;
    if (m[1] !== ' ') entry.done += 1;
  }
  return {steps, checklist};
}

// ---------------------------------------------------------------------------
// Réécriture des liens relatifs du dépôt vers les pages du site

function createLinkResolver({experiments, methodDocs}) {
  const readmeToDoc = new Map(experiments.map((e) => [
    path.join(e.dir, 'README.md'), path.join(OUT_DOCS, 'experiences', e.slug, 'index.md'),
  ]));
  const noteToDoc = new Map(experiments.filter((e) => e.hasSupervisorNote).map((e) => [
    path.join(e.dir, 'reports', 'supervisor-note.md'),
    path.join(OUT_DOCS, 'experiences', e.slug, 'fiche-superviseur.md'),
  ]));
  const methodToDoc = new Map(methodDocs.map((d) => [d.source, path.join(OUT_DOCS, 'methode', `${d.id}.md`)]));
  methodToDoc.set(path.join(ROOT, 'README.md'), path.join(OUT_DOCS, 'progression.md'));
  const experimentOf = (abs) => experiments.find((e) => abs === e.dir || abs.startsWith(e.dir + path.sep));

  /**
   * @param target  lien tel qu'écrit dans le fichier source
   * @param baseDir dossier du fichier source
   * @param outFile fichier généré qui contiendra le lien
   * @returns nouvelle cible, ou null si le lien doit devenir du texte
   */
  return function resolve(target, baseDir, outFile) {
    if (/^([a-z]+:|#|\/)/i.test(target)) return target;
    const [rawPath, hash] = target.split('#');
    const suffix = hash ? `#${hash}` : '';
    const abs = path.resolve(baseDir, decodeURI(rawPath));
    const rel = (file) => {
      const r = path.relative(path.dirname(outFile), file).split(path.sep).join('/');
      return (r.startsWith('.') ? r : `./${r}`) + suffix;
    };

    const doc = readmeToDoc.get(abs) || noteToDoc.get(abs) || methodToDoc.get(abs);
    if (doc) return rel(doc);
    // Le site ne se publie pas lui-même : le lien devient du texte.
    if (abs === SITE || abs.startsWith(SITE + path.sep)) return null;
    if (!fs.existsSync(abs)) {
      warnings.push(`lien introuvable « ${target} » dans ${path.relative(ROOT, baseDir)}`);
      return null;
    }

    const experiment = experimentOf(abs);
    const stat = fs.statSync(abs);
    if (experiment) {
      const inside = path.relative(experiment.dir, abs).split(path.sep).join('/');
      const artefacts = path.join(OUT_DOCS, 'experiences', experiment.slug, 'artefacts.md');
      if (stat.isDirectory() || isCodeFile(abs)) {
        return rel(artefacts).replace(/#.*$/, '') + `#${anchor(inside)}`;
      }
      if (abs.endsWith('.png') || abs.endsWith('.pdf') || stat.size <= MAX_COPIED_DATA) {
        const dest = path.join(OUT_DOCS, 'experiences', experiment.slug, 'assets', inside);
        copyFile(abs, dest);
        return rel(dest);
      }
      return rel(artefacts).replace(/#.*$/, '') + '#donnees-brutes';
    }

    const toolsDir = path.join(ROOT, 'tools');
    if (abs.startsWith(toolsDir + path.sep) && isCodeFile(abs)) {
      return rel(path.join(OUT_DOCS, 'methode', 'outils.md')).replace(/#.*$/, '')
        + `#${anchor(path.relative(ROOT, abs))}`;
    }
    warnings.push(`lien vers un fichier non publié « ${target} » dans ${path.relative(ROOT, baseDir)}`);
    return null;
  };
}

function isCodeFile(file) {
  const name = path.basename(file);
  return Boolean(CODE_NAMES[name] || CODE_LANGUAGES[path.extname(name)]);
}

function languageOf(file) {
  const name = path.basename(file);
  return CODE_NAMES[name] || CODE_LANGUAGES[path.extname(name)] || 'text';
}

/**
 * Réécrit les liens d'un document Markdown (hors blocs de code) et insère,
 * après le paragraphe ou la liste qui les cite, les figures PNG référencées.
 */
function transformMarkdown(markdown, {baseDir, outFile, resolve, experiment}) {
  const lines = markdown.split('\n');
  const out = [];
  const embedded = new Set();
  let pending = [];
  let inFence = null;
  let item = [];

  // Légende : texte de l'élément de liste ou du paragraphe qui cite la figure.
  const flushFigures = () => {
    for (const figure of pending) {
      const caption = plain(figure.context.join(' ').replace(/^\s*([-*+]|\d+\.)\s+/, ''))
        .replace(/^figures\/\S+\s*:\s*/, '') || figure.alt;
      out.push(`![${figure.alt}](${figure.src} ${yaml(caption)})`, '');
    }
    pending = [];
  };

  for (let i = 0; i < lines.length; i += 1) {
    let line = lines[i];
    const fenceMatch = line.match(/^\s*(`{3,}|~{3,})/);
    if (inFence) {
      if (fenceMatch && fenceMatch[1][0] === inFence[0] && fenceMatch[1].length >= inFence.length) inFence = null;
      out.push(line);
      continue;
    }
    if (fenceMatch) {
      inFence = fenceMatch[1];
      out.push(line);
      continue;
    }

    if (/^\s*([-*+]|\d+\.)\s+/.test(line) || line.trim() === '') item = [];
    item.push(line);

    line = line.replace(/(!?)\[((?:[^\]`]|`[^`]*`)*)\]\(([^)\s]+)(\s+"[^"]*")?\)/g, (whole, bang, text, target, title = '') => {
      const resolved = resolve(target, baseDir, outFile);
      if (resolved === null) return bang ? '' : text;

      // Figure citée : on l'affiche en plus du lien de téléchargement.
      if (experiment && !bang && /^figures\/[^#]+\.(pdf|png)$/.test(target)) {
        const png = path.join(baseDir, target.replace(/\.pdf$/, '.png'));
        if (fs.existsSync(png) && !embedded.has(png)) {
          embedded.add(png);
          const pngInside = path.relative(experiment.dir, png).split(path.sep).join('/');
          const dest = path.join(OUT_DOCS, 'experiences', experiment.slug, 'assets', pngInside);
          copyFile(png, dest);
          pending.push({
            png, alt: path.basename(png),
            src: `./${path.relative(path.dirname(outFile), dest).split(path.sep).join('/')}`,
            context: item,
          });
        }
      }
      return `${bang}[${text}](${resolved}${title})`;
    });
    out.push(line);

    const next = lines[i + 1];
    const blockEnds = next === undefined
      || (line.trim() === '' && !/^(\s+\S|\s*([-*+]|\d+\.)\s+)/.test(next));
    if (pending.length && blockEnds) {
      if (line.trim() !== '') out.push('');
      flushFigures();
    }
  }
  flushFigures();
  return out.join('\n');
}

// ---------------------------------------------------------------------------
// Génération des pages

function frontMatter(fields) {
  const lines = Object.entries(fields)
    .filter(([, v]) => v !== undefined && v !== null)
    .map(([k, v]) => `${k}: ${typeof v === 'string' ? yaml(v) : JSON.stringify(v)}`);
  return `---\n${lines.join('\n')}\n---\n\n`;
}

const STATUS_LABELS = {
  campagne: 'Campagne réalisée',
  'mise-au-point': 'Mise au point',
  protocole: 'Protocole en préparation',
};

function generateExperiment(experiment, resolve, checklist) {
  const outDir = path.join(OUT_DOCS, 'experiences', experiment.slug);
  const source = fs.readFileSync(path.join(experiment.dir, 'README.md'), 'utf8');
  const {body} = splitTitle(source);
  const outFile = path.join(outDir, 'index.md');

  writeText(path.join(outDir, '_category_.json'), JSON.stringify({
    label: `${experiment.code} - ${experiment.shortTitle}`,
    position: experiment.number,
    collapsed: true,
  }, null, 2) + '\n');

  const progress = checklist[experiment.code];
  const meta = [
    `**Projet ${experiment.code}** · ${STATUS_LABELS[experiment.status]}`,
    progress ? `${progress.done} étape(s) sur ${progress.total} validée(s)` : null,
    `compte rendu mis à jour le ${MONTHS.format(experiment.updated)}`,
  ].filter(Boolean).join(' · ');
  const extras = [
    experiment.hasSupervisorNote ? '[Fiche superviseur](./fiche-superviseur.md)' : null,
    '[Code, figures et données](./artefacts.md)',
    `source : \`experiments/${experiment.slug}/README.md\``,
  ].filter(Boolean).join(' · ');

  const content = transformMarkdown(body, {baseDir: experiment.dir, outFile, resolve, experiment});
  writeText(outFile, frontMatter({
    title: `${experiment.code} - ${experiment.fullTitle}`,
    sidebar_label: 'Compte rendu',
    sidebar_position: 1,
    description: experiment.question || undefined,
    pagination_label: `${experiment.code} - ${experiment.shortTitle}`,
  }) + `:::info[Fiche du projet]\n\n${meta}\n\n${extras}\n\n:::\n\n${content}`);

  if (experiment.hasSupervisorNote) {
    const noteSource = path.join(experiment.dir, 'reports', 'supervisor-note.md');
    const noteFile = path.join(outDir, 'fiche-superviseur.md');
    const note = splitTitle(fs.readFileSync(noteSource, 'utf8'));
    writeText(noteFile, frontMatter({
      title: `${experiment.code} - ${note.title || 'Fiche superviseur'}`,
      sidebar_label: 'Fiche superviseur',
      sidebar_position: 2,
    }) + transformMarkdown(note.body, {baseDir: path.dirname(noteSource), outFile: noteFile, resolve, experiment}));
  }

  generateArtefacts(experiment, outDir);
}

function generateArtefacts(experiment, outDir) {
  const {dir, slug, code} = experiment;
  const outFile = path.join(outDir, 'artefacts.md');
  const parts = [frontMatter({
    title: `${code} - Code, figures et données`,
    sidebar_label: 'Code, figures et données',
    sidebar_position: 3,
    toc_max_heading_level: 2,
  })];
  parts.push(`Page générée automatiquement à partir du dossier \`experiments/${slug}/\`. `
    + 'Les chemins sont relatifs à ce dossier.\n');

  // Reproduction : cibles du Makefile.
  const makefile = path.join(dir, 'Makefile');
  if (fs.existsSync(makefile)) {
    const phony = fs.readFileSync(makefile, 'utf8').match(/^\.PHONY:\s*(.+)$/m);
    const targets = phony
      ? phony[1].trim().split(/\s+/).filter((t) => t !== 'all')
      : [...fs.readFileSync(makefile, 'utf8').matchAll(/^([a-z][\w-]*):/gm)].map((m) => m[1]);
    parts.push('## Reproduire {#reproduire}\n', '```sh', `cd experiments/${slug}`,
      ...targets.map((t) => `make ${t}`), '```\n');
  }

  // Figures : toutes, groupées par préfixe (campaign, quick, ...).
  const figures = walk(path.join(dir, 'figures')).filter((f) => /\.(png|svg|jpe?g)$/.test(f));
  if (figures.length) {
    parts.push('## Figures {#figures}\n');
    const groups = new Map();
    for (const figure of figures) {
      const prefix = figure.split(/[-.]/)[0];
      if (!groups.has(prefix)) groups.set(prefix, []);
      groups.get(prefix).push(figure);
    }
    const groupTitle = {campaign: 'Campagne', quick: 'Vérification rapide (chaîne de traitement, non probante)'};
    for (const [prefix, files] of groups) {
      parts.push(`### ${groupTitle[prefix] || prefix} {#figures-${anchor(prefix)}}\n`);
      for (const figure of files) {
        const inside = `figures/${figure}`;
        const dest = path.join(outDir, 'assets', inside);
        copyFile(path.join(dir, inside), dest);
        const pdf = inside.replace(/\.\w+$/, '.pdf');
        let caption = `${inside}`;
        if (fs.existsSync(path.join(dir, pdf))) {
          copyFile(path.join(dir, pdf), path.join(outDir, 'assets', pdf));
          parts.push(`![${figure}](./assets/${inside} ${yaml(caption)})\n`,
            `[Version vectorielle PDF](./assets/${pdf}) · [PNG 600 dpi](./assets/${inside})\n`);
        } else {
          parts.push(`![${figure}](./assets/${inside} ${yaml(caption)})\n`);
        }
      }
    }
  }

  // Code source : src/ puis fichiers à la racine de l'expérience.
  const codeFiles = [
    ...walk(path.join(dir, 'src')).map((f) => `src/${f}`),
    ...fs.readdirSync(dir).filter((f) => fs.statSync(path.join(dir, f)).isFile() && f !== 'README.md').sort(),
  ].filter((f) => isCodeFile(f) && fs.statSync(path.join(dir, f)).size <= MAX_EMBEDDED_CODE && isText(path.join(dir, f)));
  const otherSources = walk(path.join(dir, 'src')).map((f) => `src/${f}`).filter((f) => !codeFiles.includes(f));
  if (codeFiles.length || otherSources.length) {
    parts.push('## Code source {#code-source}\n');
    parts.push('| Fichier | Taille |', '|---|---|',
      ...codeFiles.map((f) => `| [\`${f}\`](#${anchor(f)}) | ${humanSize(fs.statSync(path.join(dir, f)).size)} |`),
      '');
    for (const file of codeFiles) {
      const content = fs.readFileSync(path.join(dir, file), 'utf8').replace(/\s+$/, '');
      const f = fence(content);
      parts.push(`### \`${file}\` {#${anchor(file)}}\n`,
        `${f}${languageOf(file)} title="${file}" showLineNumbers`, content, `${f}\n`);
    }
    for (const file of otherSources) {
      parts.push(`### \`${file}\` {#${anchor(file)}}\n`, 'Fichier non textuel ou trop volumineux pour être affiché.\n');
    }
  }

  // Rapports calculés : copiés et téléchargeables.
  const reportsDir = path.join(dir, 'reports');
  const reports = walk(reportsDir).filter((f) => f !== 'supervisor-note.md');
  if (reports.length) {
    parts.push('## Rapports calculés {#rapports}\n', '| Fichier | Taille |', '|---|---|');
    const listedDirs = new Set();
    for (const file of reports) {
      const inside = `reports/${file}`;
      const subdir = path.dirname(inside);
      if (subdir !== 'reports' && !listedDirs.has(subdir)) {
        listedDirs.add(subdir);
      }
      copyFile(path.join(dir, inside), path.join(outDir, 'assets', inside));
      parts.push(`| [\`${inside}\`](./assets/${inside}) | ${humanSize(fs.statSync(path.join(dir, inside)).size)} |`);
    }
    parts.push('');
    for (const subdir of listedDirs) {
      parts.push(`### \`${subdir}/\` {#${anchor(subdir + '/')}}\n`,
        `Fichiers listés dans le tableau ci-dessus sous \`${subdir}/\`.\n`);
    }
  }

  // Données brutes : inventaire (conservées dans le dépôt, petits fichiers copiés).
  const dataDir = path.join(dir, 'data');
  if (fs.existsSync(dataDir)) {
    parts.push('## Données brutes {#donnees-brutes}\n',
      'Les données brutes restent dans le dépôt ; seuls les fichiers de moins de '
      + `${humanSize(MAX_COPIED_DATA)} sont téléchargeables depuis le site.\n`,
      '| Élément | Contenu | Taille |', '|---|---|---|');
    const subdirs = [];
    for (const entry of fs.readdirSync(dataDir, {withFileTypes: true}).sort((a, b) => a.name.localeCompare(b.name))) {
      const inside = `data/${entry.name}`;
      const full = path.join(dir, inside);
      if (entry.isDirectory()) {
        const {count, size} = dirStats(full);
        subdirs.push({inside, full});
        parts.push(`| [\`${inside}/\`](#${anchor(inside + '/')}) | ${count} fichier(s) | ${humanSize(size)} |`);
      } else {
        const size = fs.statSync(full).size;
        let label = `\`${inside}\``;
        if (size <= MAX_COPIED_DATA) {
          copyFile(full, path.join(outDir, 'assets', inside));
          label = `[\`${inside}\`](./assets/${inside})`;
        }
        parts.push(`| ${label} | fichier | ${humanSize(size)} |`);
      }
    }
    parts.push('');
    for (const {inside, full} of subdirs) {
      const files = walk(full);
      const shown = files.slice(0, 12).map((f) => `\`${f}\``).join(', ');
      parts.push(`### \`${inside}/\` {#${anchor(inside + '/')}}\n`,
        `${files.length} fichier(s) : ${shown}${files.length > 12 ? ', ...' : ''}\n`);
    }
  }

  writeText(outFile, parts.join('\n'));
}

function generateExperimentsOverview(experiments, checklist) {
  const rows = experiments.map((e) => {
    const progress = checklist[e.code];
    return `| [${e.code}](./${e.slug}/index.md) | ${e.fullTitle} | ${STATUS_LABELS[e.status]} | `
      + `${progress ? `${progress.done}/${progress.total}` : '-'} | ${MONTHS.format(e.updated)} |`;
  });
  writeText(path.join(OUT_DOCS, 'experiences', '_category_.json'), JSON.stringify({
    label: 'Expériences', position: 2, collapsed: false,
  }, null, 2) + '\n');
  writeText(path.join(OUT_DOCS, 'experiences', 'index.md'), frontMatter({
    title: 'Expériences',
    description: 'Liste des expériences du laboratoire, générée à partir du dossier experiments/.',
  }) + [
    'Chaque expérience suit le même format : question, notions, prédictions écrites avant la mesure, '
    + 'code, vérification indépendante, protocole, données brutes, figures, interprétation, limites '
    + 'et questions de compréhension.',
    '',
    '| Projet | Titre | État | Étapes | Mise à jour |',
    '|---|---|---|---|---|',
    ...rows,
    '',
    ...experiments.flatMap((e) => [
      `## ${e.code} - ${e.shortTitle} {#${anchor(e.code)}}`,
      '',
      e.question ? `**Question :** ${e.question}` : '',
      '',
      `[Compte rendu](./${e.slug}/index.md)`
        + (e.hasSupervisorNote ? ` · [Fiche superviseur](./${e.slug}/fiche-superviseur.md)` : '')
        + ` · [Code, figures et données](./${e.slug}/artefacts.md)`,
      '',
    ]),
  ].join('\n'));
}

function generateProgression(experiments, resolve) {
  const source = path.join(ROOT, 'README.md');
  if (!fs.existsSync(source)) return;
  const outFile = path.join(OUT_DOCS, 'progression.md');
  const {title, body} = splitTitle(fs.readFileSync(source, 'utf8'));
  const byCode = new Map(experiments.map((e) => [e.code, e]));
  let content = transformMarkdown(body, {baseDir: ROOT, outFile, resolve});
  // Les codes de projet du tableau pointent vers les expériences publiées.
  content = content.replace(/^\|\s*([A-Z]\d+)\s*\|/gm, (whole, code) => (
    byCode.has(code) ? `| [${code}](./experiences/${byCode.get(code).slug}/index.md) |` : whole
  ));
  writeText(outFile, frontMatter({
    title: title || 'Progression',
    sidebar_label: 'Progression',
    sidebar_position: 1,
    slug: '/progression',
  }) + content);
}

function generateMethod(methodDocs, resolve) {
  writeText(path.join(OUT_DOCS, 'methode', '_category_.json'), JSON.stringify({
    label: 'Méthode et références', position: 3, collapsed: false,
  }, null, 2) + '\n');
  for (const doc of methodDocs) {
    const outFile = path.join(OUT_DOCS, 'methode', `${doc.id}.md`);
    const {body} = splitTitle(fs.readFileSync(doc.source, 'utf8'));
    writeText(outFile, frontMatter({title: doc.title, sidebar_position: doc.position})
      + transformMarkdown(body, {baseDir: path.dirname(doc.source), outFile, resolve}));
  }

  const toolsDir = path.join(ROOT, 'tools');
  const tools = walk(toolsDir).filter((f) => isCodeFile(f));
  if (tools.length) {
    const parts = [frontMatter({title: 'Outils partagés', sidebar_position: 50, toc_max_heading_level: 2})];
    parts.push('Modules communs à toutes les expériences, publiés depuis le dossier `tools/`.\n');
    for (const file of tools) {
      const rel = `tools/${file}`;
      const content = fs.readFileSync(path.join(toolsDir, file), 'utf8').replace(/\s+$/, '');
      const f = fence(content);
      parts.push(`## \`${rel}\` {#${anchor(rel)}}\n`, `${f}${languageOf(file)} title="${rel}" showLineNumbers`, content, `${f}\n`);
    }
    writeText(path.join(OUT_DOCS, 'methode', 'outils.md'), parts.join('\n'));
  }
}

function generateHomeData(experiments, progression) {
  const byCode = new Map(experiments.map((e) => [e.code, e]));
  const data = {
    generatedAt: new Date().toISOString(),
    experiments: experiments.map((e) => {
      let thumbnail = null;
      if (e.thumbnail) {
        const dest = path.join(OUT_STATIC, e.slug, e.thumbnail);
        copyFile(path.join(e.dir, 'figures', e.thumbnail), dest);
        thumbnail = `/generated/${e.slug}/${e.thumbnail}`;
      }
      return {
        slug: e.slug, code: e.code, title: e.fullTitle, shortTitle: e.shortTitle,
        question: e.question, status: e.status, statusLabel: STATUS_LABELS[e.status],
        progress: progression.checklist[e.code] || null,
        hasSupervisorNote: e.hasSupervisorNote, thumbnail,
        figureCount: e.figures.length,
        updated: MONTHS.format(e.updated),
      };
    }),
    roadmap: progression.steps.map((s) => ({
      ...s,
      slug: byCode.get(s.code)?.slug || null,
      status: byCode.get(s.code)?.status || 'a-venir',
    })),
  };
  // Les experiences hors du tableau de progression restent visibles.
  for (const e of experiments) {
    if (!progression.steps.some((s) => s.code === e.code)) {
      data.roadmap.push({code: e.code, project: e.shortTitle, goal: '', dependsOn: '', slug: e.slug, status: e.status});
    }
  }
  const content = JSON.stringify(data, null, 2) + '\n';
  // La date de génération ne doit pas déclencher de rechargement à elle seule.
  const file = path.join(OUT_DATA, 'experiences.json');
  if (fs.existsSync(file)) {
    const previous = JSON.parse(fs.readFileSync(file, 'utf8'));
    if (JSON.stringify({...previous, generatedAt: null}) === JSON.stringify({...data, generatedAt: null})) {
      generated.add(file);
      return;
    }
  }
  writeText(file, content);
}

// ---------------------------------------------------------------------------

function sync() {
  const started = Date.now();
  generated.clear();
  warnings.length = 0;

  const experiments = discoverExperiments();
  const methodDocs = discoverMethodDocs();
  const progression = readProgression();
  const resolve = createLinkResolver({experiments, methodDocs});

  generateProgression(experiments, resolve);
  generateExperimentsOverview(experiments, progression.checklist);
  for (const experiment of experiments) generateExperiment(experiment, resolve, progression.checklist);
  generateMethod(methodDocs, resolve);
  generateHomeData(experiments, progression);

  pruneStale(OUT_DOCS);
  pruneStale(OUT_DATA);
  pruneStale(OUT_STATIC);

  for (const warning of new Set(warnings)) console.warn(`[sync] attention : ${warning}`);
  console.log(`[sync] ${experiments.length} expérience(s) publiée(s) : `
    + `${experiments.map((e) => e.code).join(', ') || 'aucune'} (${Date.now() - started} ms)`);
}

function watch(command) {
  const child = spawn(command[0], command.slice(1), {stdio: 'inherit', shell: false,
    env: {...process.env, PATH: `${path.join(SITE, 'node_modules', '.bin')}${path.delimiter}${process.env.PATH}`}});
  child.on('exit', (code) => process.exit(code ?? 0));
  for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));

  let timer = null;
  const schedule = (filename) => {
    if (filename && filename.split(path.sep).some((p) => IGNORED_DIRS.has(p))) return;
    clearTimeout(timer);
    timer = setTimeout(() => {
      try {
        sync();
      } catch (error) {
        console.error('[sync] échec :', error);
      }
    }, 400);
  };
  const targets = [EXPERIMENTS, path.join(ROOT, 'docs'), path.join(ROOT, 'tools')];
  for (const target of targets) {
    if (fs.existsSync(target)) fs.watch(target, {recursive: true}, (_, filename) => schedule(filename));
  }
  for (const file of ['README.md', 'STYLE_FIGURES.md']) {
    const full = path.join(ROOT, file);
    if (fs.existsSync(full)) fs.watchFile(full, {interval: 1000}, () => schedule(file));
  }
  console.log('[sync] surveillance de experiments/, docs/, tools/, README.md et STYLE_FIGURES.md');
}

sync();
const separator = process.argv.indexOf('--');
if (process.argv.includes('--watch')) {
  if (separator === -1 || separator === process.argv.length - 1) {
    console.error('usage : sync-content.mjs --watch -- <commande>');
    process.exit(2);
  }
  watch(process.argv.slice(separator + 1));
}
