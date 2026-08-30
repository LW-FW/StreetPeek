// components/SchoolsSummary.tsx
// Compact summary card for the Overview tab — stats + top 3 nearest only,
// no filters and no map. Full detail lives in the dedicated "Schools" tab;
// this links there. Styled as one of Overview's dark-header cards (see
// .card/.cardHeader in styles/Results.module.css) rather than the plain
// panel look NearbySummary uses, since this sits directly among those
// cards. Data is fetched once by the parent Results page and passed in.

import type { EducationResponse, SchoolResult, NurseryResult } from '../pages/api/schools';
import styles from './SchoolsSummary.module.css';

interface Props {
  data: EducationResponse | null;
  loading: boolean;
  onViewAll?: () => void;
  onRetry?: () => void;
}

function formatDistance(miles: number): string {
  if (miles < 0.1) return `${Math.round(miles * 1760)}yds`;
  return `${miles.toFixed(2)}mi`;
}

export default function SchoolsSummary({ data, loading, onViewAll, onRetry }: Props) {
  if (loading) {
    return (
      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <h2 className={styles.cardTitle}>🏫 Schools &amp; Nurseries</h2>
        </div>
        <div className={styles.body}>
          <div className={styles.loading}>
            <div className={styles.spinner} />
            <span>Finding nearby schools and nurseries…</span>
          </div>
        </div>
      </section>
    );
  }

  if (!data) {
    return (
      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <h2 className={styles.cardTitle}>🏫 Schools &amp; Nurseries</h2>
        </div>
        <div className={styles.body}>
          <p className={styles.errorMsg}>Couldn&apos;t reach school data right now.</p>
          {onRetry && <button className={styles.retryBtn} onClick={onRetry}>Try again</button>}
        </div>
      </section>
    );
  }

  const { schools, nurseries, summary } = data;

  const combined: Array<{ id: string; name: string; distanceMiles: number; kind: 'school' | 'nursery' }> = [
    ...schools.map((s: SchoolResult) => ({ id: s.id, name: s.name, distanceMiles: s.distanceMiles, kind: 'school' as const })),
    ...nurseries.map((n: NurseryResult) => ({ id: n.id, name: n.name, distanceMiles: n.distanceMiles, kind: 'nursery' as const })),
  ].sort((a, b) => a.distanceMiles - b.distanceMiles).slice(0, 3);

  return (
    <section className={styles.card}>
      <div className={styles.cardHeader}>
        <h2 className={styles.cardTitle}>🏫 Schools &amp; Nurseries</h2>
      </div>

      <div className={styles.body}>
        <div className={styles.statsRow}>
          <div className={styles.stat}>
            <span className={styles.statNum}>{schools.length}</span>
            <span className={styles.statLabel}>Schools</span>
          </div>
          <div className={styles.statDivider} />
          <div className={styles.stat}>
            <span className={styles.statNum}>{nurseries.length}</span>
            <span className={styles.statLabel}>Nurseries</span>
          </div>
          <div className={styles.statDivider} />
          <div className={styles.stat}>
            <span className={summary.nearestPrimary || summary.nearestSecondary ? styles.statNum : `${styles.statNum} ${styles.statNumMuted}`}>
              {schools[0] ? formatDistance(schools[0].distanceMiles) : '—'}
            </span>
            <span className={styles.statLabel}>Nearest school</span>
          </div>
          <div className={styles.statDivider} />
          <div className={styles.stat}>
            <span className={summary.nearestNursery ? styles.statNum : `${styles.statNum} ${styles.statNumMuted}`}>
              {summary.nearestNursery ? formatDistance(summary.nearestNursery.distanceMiles) : '—'}
            </span>
            <span className={styles.statLabel}>Nearest nursery</span>
          </div>
        </div>

        <div className={styles.callout}>
          <span className={styles.calloutIcon}>ℹ️</span>
          <div>
            <span className={styles.calloutLabel}>Ofsted ratings are mid-change</span>
            <p className={styles.calloutText}>
              Schools show either an old single grade or Ofsted&apos;s new category-by-category report card, whichever they last received. Nurseries stay on the old scale and refresh monthly.
            </p>
          </div>
        </div>

        {combined.length > 0 && (
          <ul className={styles.nearList}>
            {combined.map(item => (
              <li key={item.id} className={styles.nearRow}>
                <span className={styles.nearName}>{item.name}</span>
                <span className={styles.nearDist}>{formatDistance(item.distanceMiles)}</span>
              </li>
            ))}
          </ul>
        )}

        {onViewAll && (
          <button className={styles.viewAllBtn} onClick={onViewAll}>
            View all Schools &amp; Nurseries
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M4.5 2.5L8 6l-3.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        )}
      </div>
    </section>
  );
}
