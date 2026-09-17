import React from 'react';
import Link from '@docusaurus/Link';
import useBaseUrl from '@docusaurus/useBaseUrl';
import Layout from '@theme/Layout';
import data from '@site/src/data/experiences.json';
import styles from './index.module.css';

// Page d'accueil : alimentée par src/data/experiences.json, que
// scripts/sync-content.mjs régénère à partir du dossier experiments/.

const METHOD = [
  'Question',
  'Modèle de coût',
  'Prédiction',
  'Implémentation',
  'Vérification',
  'Mesure',
  'Visualisation',
  'Interprétation',
  'Expérience de contrôle',
];

function ExperimentCard({experiment}) {
  const thumbnail = useBaseUrl(experiment.thumbnail || '');
  const base = `/experiences/${experiment.slug}`;
  return (
    <article className={styles.card}>
      {experiment.thumbnail && (
        <Link to={base} className={styles.thumbnail} tabIndex={-1} aria-hidden="true">
          <img src={thumbnail} alt="" loading="lazy" />
        </Link>
      )}
      <div className={styles.cardBody}>
        <div className={styles.cardMeta}>
          <span className={styles.code}>{experiment.code}</span>
          <span className={styles[`status-${experiment.status}`]}>{experiment.statusLabel}</span>
        </div>
        <h3 className={styles.cardTitle}>
          <Link to={base}>{experiment.shortTitle}</Link>
        </h3>
        {experiment.question && <p className={styles.question}>{experiment.question}</p>}
        <div className={styles.cardLinks}>
          <Link to={base}>Compte rendu</Link>
          {experiment.hasSupervisorNote && <Link to={`${base}/fiche-superviseur`}>Fiche superviseur</Link>}
          <Link to={`${base}/artefacts`}>Code et données</Link>
        </div>
        <p className={styles.updated}>
          Mis à jour le {experiment.updated}
          {experiment.figureCount > 0 && ` · ${experiment.figureCount} figure(s)`}
        </p>
      </div>
    </article>
  );
}

function Roadmap({steps}) {
  const groups = [];
  for (const step of steps) {
    const letter = step.code.replace(/\d.*$/, '');
    let group = groups.find((g) => g.letter === letter);
    if (!group) {
      group = {letter, steps: []};
      groups.push(group);
    }
    group.steps.push(step);
  }
  return (
    <ol className={styles.roadmap}>
      {groups.map((group) => (
        <li key={group.letter} className={styles.roadmapGroup}>
          <span className={styles.roadmapLetter}>{group.letter}</span>
          <ul>
            {group.steps.map((step) => (
              <li key={step.code} className={step.slug ? styles.stepDone : styles.stepTodo}>
                {step.slug ? (
                  <Link to={`/experiences/${step.slug}`} title={step.goal}>
                    <strong>{step.code}</strong> {step.project}
                  </Link>
                ) : (
                  <span title={step.goal}>
                    <strong>{step.code}</strong> {step.project}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </li>
      ))}
    </ol>
  );
}

export default function Home() {
  const published = data.experiments.length;
  const planned = data.roadmap.length;
  return (
    <Layout
      title="Accueil"
      description="Laboratoire d'apprentissage progressif en programmation système, performance et systèmes distribués sous Linux.">
      <header className={styles.hero}>
        <div className="container">
          <p className={styles.kicker}>Laboratoire d'apprentissage reproductible</p>
          <h1 className={styles.title}>Systèmes, performance et distribué sous Linux</h1>
          <p className={styles.lead}>
            De petits projets exécutables, documentés et reproductibles. Chaque résultat décrit la
            machine et le protocole documentés, pas une constante universelle.
          </p>
          <ol className={styles.method} aria-label="Démarche suivie par chaque expérience">
            {METHOD.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
          <div className={styles.actions}>
            <Link className="button button--primary" to="/experiences">
              Consulter les expériences
            </Link>
            <Link className="button button--secondary button--outline" to="/progression">
              Progression du laboratoire
            </Link>
          </div>
        </div>
      </header>

      <main className="container">
        <section className={styles.section}>
          <div className={styles.sectionHead}>
            <h2>Expériences publiées</h2>
            <p>
              {published} expérience(s) sur {planned} prévue(s). Chaque dossier ajouté dans{' '}
              <code>experiments/</code> apparaît ici automatiquement.
            </p>
          </div>
          <div className={styles.grid}>
            {[...data.experiments].reverse().map((experiment) => (
              <ExperimentCard key={experiment.slug} experiment={experiment} />
            ))}
          </div>
        </section>

        {data.roadmap.length > 0 && (
          <section className={styles.section}>
            <div className={styles.sectionHead}>
              <h2>Feuille de route</h2>
              <p>
                Chemin principal : A, puis B, C et D, puis F, G et H, puis I et J, K et enfin L. Les
                projets en couleur ont une page publiée.
              </p>
            </div>
            <Roadmap steps={data.roadmap} />
          </section>
        )}
      </main>
    </Layout>
  );
}
