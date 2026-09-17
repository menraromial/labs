// Configuration du site du laboratoire.
// Le contenu de docs/ est généré par scripts/sync-content.mjs : ne pas l'éditer.

import {themes as prismThemes} from 'prism-react-renderer';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import remarkFigure from './src/plugins/remark-figure.js';

const title = 'Laboratoire Linux : systèmes, performance et distribué';

/** @type {import('@docusaurus/types').Config} */
const config = {
  title,
  tagline: 'Question, modèle de coût, prédiction, implémentation, vérification, mesure, visualisation, interprétation, contrôle',
  favicon: 'img/favicon.svg',

  // Adresse de publication : à définir par variables d'environnement
  // (par exemple SITE_URL=https://utilisateur.github.io BASE_URL=/Labs/).
  url: process.env.SITE_URL || 'https://localhost',
  baseUrl: process.env.BASE_URL || '/',
  trailingSlash: false,

  // Un lien cassé dans un README ne doit pas empêcher la publication automatique
  // d'une nouvelle expérience : il est signalé, pas bloquant.
  onBrokenLinks: 'warn',
  onBrokenAnchors: 'warn',

  i18n: {defaultLocale: 'fr', locales: ['fr']},

  markdown: {
    // Les .md sont lus en CommonMark : « < », « { » et le HTML des comptes
    // rendus s'affichent tels quels, sans erreur de compilation MDX.
    format: 'detect',
    mermaid: true,
    hooks: {onBrokenMarkdownLinks: 'warn', onBrokenMarkdownImages: 'warn'},
  },

  themes: [
    '@docusaurus/theme-mermaid',
    [
      '@easyops-cn/docusaurus-search-local',
      /** @type {import('@easyops-cn/docusaurus-search-local').PluginOptions} */
      ({
        hashed: true,
        language: ['fr'],
        docsRouteBasePath: '/',
        indexBlog: false,
        indexPages: false,
        highlightSearchTermsOnTargetPage: true,
        explicitSearchResultPath: true,
      }),
    ],
  ],

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          routeBasePath: '/',
          sidebarPath: './sidebars.js',
          // Les URL gardent le nom du dossier (experiences/05-memory-traversal) ;
          // l'ordre vient de sidebar_position et des _category_.json générés.
          numberPrefixParser: false,
          beforeDefaultRemarkPlugins: [remarkFigure],
          remarkPlugins: [remarkMath],
          rehypePlugins: [rehypeKatex],
          showLastUpdateTime: false,
          breadcrumbs: true,
        },
        blog: false,
        theme: {customCss: './src/css/custom.css'},
      }),
    ],
  ],

  // Polices et feuille KaTeX servies par le site lui-même (aucun appel externe).
  clientModules: ['./src/client-styles.js'],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      colorMode: {respectPrefersColorScheme: true},
      docs: {sidebar: {hideable: true, autoCollapseCategories: false}},
      tableOfContents: {minHeadingLevel: 2, maxHeadingLevel: 3},
      navbar: {
        title: 'Laboratoire Linux',
        logo: {alt: 'Laboratoire Linux', src: 'img/logo.svg'},
        hideOnScroll: false,
        items: [
          {to: '/progression', label: 'Progression', position: 'left'},
          {to: '/experiences', label: 'Expériences', position: 'left'},
          {to: '/methode/glossaire', label: 'Glossaire', position: 'left'},
          {to: '/methode/style-figures', label: 'Méthode', position: 'left'},
          {type: 'search', position: 'right'},
        ],
      },
      footer: {
        style: 'light',
        links: [
          {
            title: 'Laboratoire',
            items: [
              {label: 'Progression', to: '/progression'},
              {label: 'Expériences', to: '/experiences'},
            ],
          },
          {
            title: 'Références',
            items: [
              {label: 'Glossaire', to: '/methode/glossaire'},
              {label: 'Environnement observé', to: '/methode/environnement'},
              {label: 'Style des figures', to: '/methode/style-figures'},
            ],
          },
        ],
        copyright: `Les résultats décrivent la machine et le protocole documentés, pas une constante universelle. ${new Date().getFullYear()}.`,
      },
      prism: {
        theme: prismThemes.github,
        darkTheme: prismThemes.vsDark,
        additionalLanguages: ['bash', 'makefile', 'toml', 'diff', 'csv'],
      },
      mermaid: {theme: {light: 'neutral', dark: 'dark'}},
    }),
};

export default config;
