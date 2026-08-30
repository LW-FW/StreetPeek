// components/NearbySummary.tsx
// Compact summary card for the Overview tab — stats + convenience callout
// only, no place list and no map. Full detail (map, filters, grouped list)
// lives in the dedicated "Nearby" tab; this links there.
//
// Data is fetched once by the parent Results page and passed in as props
// rather than fetched here — this component (and the Nearby tab it links
// to) used to fetch independently on mount, which meant every tab switch
// unmounted and remounted them, re-hitting the Overpass API each time.

import type { NearbyResponse } from '../pages/api/nearby';
import styles from './NearbySummary.module.css';

interface Props {
  data: NearbyResponse | null;
  loading: boolean;
  onViewAll?: () => void;
  onRetry?: () => void;
}

const BADGE_MAP = {
  'well-served': { label: 'Well served', cls: 'badgeWellServed' },
  moderate:      { label: 'Moderate',    cls: 'badgeModerate' },
  limited:       { label: 'Limited',     cls: 'badgeLimited' },
} as const;

function formatDistance(miles: number): string {
  if (miles < 0.1) return `${Math.round(miles * 1760)}yds`;
  return `${miles.toFixed(1)} mi`;
}

export default function NearbySummary({ data, loading, onViewAll, onRetry }: Props) {
  if (loading) {
    return (
      <section className={styles.panel}>
        <div className={styles.header}>
          <div className={styles.titleRow}>
            <span className={styles.titleIcon}>
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                <circle cx="9" cy="9" r="7" stroke="currentColor" strokeWidth="1.4"/>
                <path d="M9 5v4l3 2" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
              </svg>
            </span>
            <h2 className={styles.title}>Nearby Amenities</h2>
          </div>
        </div>
        <div className={styles.loading}>
          <div className={styles.spinner} />
          <span>Finding nearby GPs, dentists and shops…</span>
        </div>
      </section>
    );
  }

  if (!data || !data.ok) {
    return (
      <section className={styles.panel}>
        <div className={styles.header}>
          <h2 className={styles.title}>Nearby Amenities</h2>
        </div>
        <p className={styles.errorMsg}>Couldn't reach nearby amenities data right now.</p>
        {onRetry && <button className={styles.retryBtn} onClick={onRetry}>Try again</button>}
      </section>
    );
  }

  const { summary } = data;
  const { label, cls } = BADGE_MAP[summary.convenienceScore];

  return (
    <section className={styles.panel}>
      <div className={styles.header}>
        <div className={styles.titleRow}>
          <span className={styles.titleIcon}>
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <circle cx="9" cy="9" r="7" stroke="currentColor" strokeWidth="1.4"/>
              <path d="M9 5v4l3 2" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
            </svg>
          </span>
          <h2 className={styles.title}>Nearby Amenities</h2>
        </div>
        <span className={`${styles.badge} ${styles[cls]}`}>{label}</span>
      </div>

      <div className={styles.statsRow}>
        <div className={styles.stat}>
          <span className={summary.nearestGP ? styles.statNum : `${styles.statNum} ${styles.statNumMuted}`}>
            {summary.nearestGP ? formatDistance(summary.nearestGP.distanceMiles) : '—'}
          </span>
          <span className={styles.statLabel}>Nearest GP</span>
        </div>
        <div className={styles.statDivider} />
        <div className={styles.stat}>
          <span className={summary.nearestDentist ? styles.statNum : `${styles.statNum} ${styles.statNumMuted}`}>
            {summary.nearestDentist ? formatDistance(summary.nearestDentist.distanceMiles) : '—'}
          </span>
          <span className={styles.statLabel}>Nearest dentist</span>
        </div>
        <div className={styles.statDivider} />
        <div className={styles.stat}>
          <span className={summary.nearestPharmacy ? styles.statNum : `${styles.statNum} ${styles.statNumMuted}`}>
            {summary.nearestPharmacy ? formatDistance(summary.nearestPharmacy.distanceMiles) : '—'}
          </span>
          <span className={styles.statLabel}>Nearest pharmacy</span>
        </div>
        <div className={styles.statDivider} />
        <div className={styles.stat}>
          <span className={styles.statNum}>{summary.supermarketsNearby}</span>
          <span className={styles.statLabel}>Supermarkets within {summary.radiusMiles}mi</span>
        </div>
      </div>

      <div className={`${styles.callout} ${styles[`convenience_${summary.convenienceScore}`]}`}>
        <span className={styles.calloutIcon}>
          {summary.convenienceScore === 'well-served' && '✅'}
          {summary.convenienceScore === 'moderate' && '⚠️'}
          {summary.convenienceScore === 'limited' && '🚗'}
        </span>
        <div>
          <span className={styles.calloutLabel}>Day-to-day convenience</span>
          <p className={styles.calloutText}>{summary.convenienceReason}</p>
        </div>
      </div>

      {onViewAll && (
        <button className={styles.viewAllBtn} onClick={onViewAll}>
          View all nearby GPs, shops &amp; more
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M4.5 2.5L8 6l-3.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      )}
    </section>
  );
}
