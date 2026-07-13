// components/NearbyPanel.tsx
// GPs, dentists, pharmacies and shops within walking distance.
//
// Usage in results.tsx:
//   import NearbyPanel from '../components/NearbyPanel';
//   ...
//   {location && <NearbyPanel lat={location.lat} lng={location.lng} />}

import { useEffect, useState } from 'react';
import type { NearbyPlace, NearbyResponse } from '../pages/api/nearby';
import styles from '../styles/NearbyPanel.module.css';

interface Props {
  lat: number;
  lng: number;
}

// ─── small helpers ────────────────────────────────────────────────────────────

const BADGE_MAP = {
  'well-served': { label: 'Well served', cls: 'badgeWellServed' },
  moderate:      { label: 'Moderate',    cls: 'badgeModerate' },
  limited:       { label: 'Limited',     cls: 'badgeLimited' },
} as const;

function ConvenienceBadge({ score }: { score: NearbyResponse['summary']['convenienceScore'] }) {
  const { label, cls } = BADGE_MAP[score];
  return <span className={`${styles.badge} ${styles[cls]}`}>{label}</span>;
}

const TYPE_LABELS: Record<NearbyPlace['type'], string> = {
  gp: 'GP',
  dentist: 'Dentist',
  pharmacy: 'Pharmacy',
  supermarket: 'Supermarket',
  convenience: 'Convenience store',
};

function TypeIcon({ type }: { type: NearbyPlace['type'] }) {
  if (type === 'gp') {
    return (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-label="GP">
        <path d="M8 2v5M8 9v5M5.5 4.5h5M5.5 11.5h5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
        <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeWidth="1.2"/>
      </svg>
    );
  }
  if (type === 'dentist') {
    return (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-label="Dentist">
        <path d="M8 2.5c-1.5 0-2.5 1-3.5 1-1.2 0-2 .9-2 2.2 0 2 1 4.5 1.6 6.3.3.9.6 1.5 1.2 1.5.7 0 .9-1.8 1.2-3 .2-.8.5-1.3 1.5-1.3s1.3.5 1.5 1.3c.3 1.2.5 3 1.2 3 .6 0 .9-.6 1.2-1.5.6-1.8 1.6-4.3 1.6-6.3 0-1.3-.8-2.2-2-2.2-1 0-2-1-3.5-1z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round"/>
      </svg>
    );
  }
  if (type === 'pharmacy') {
    return (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-label="Pharmacy">
        <path d="M8 3v10M3 8h10" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
        <rect x="2" y="2" width="12" height="12" rx="2.5" stroke="currentColor" strokeWidth="1.2"/>
      </svg>
    );
  }
  if (type === 'convenience') {
    return (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-label="Convenience store">
        <path d="M2.5 6.5h11l-.8 6.5a1 1 0 0 1-1 .9H4.3a1 1 0 0 1-1-.9l-.8-6.5z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round"/>
        <path d="M5 6.5V5a3 3 0 0 1 6 0v1.5" stroke="currentColor" strokeWidth="1.3"/>
      </svg>
    );
  }
  // supermarket
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-label="Supermarket">
      <path d="M2 4h1.5l1 7.5a1.2 1.2 0 0 0 1.2 1h6.1a1.2 1.2 0 0 0 1.2-1L14 6H4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
      <circle cx="6.5" cy="14" r="1" fill="currentColor"/>
      <circle cx="11" cy="14" r="1" fill="currentColor"/>
    </svg>
  );
}

function formatDistance(miles: number): string {
  if (miles < 0.1) return `${Math.round(miles * 1760)}yds`;
  return `${miles.toFixed(1)} mi`;
}

function walkMins(miles: number): number {
  return Math.round((miles / 3) * 60);
}

// ─── main component ───────────────────────────────────────────────────────────

export default function NearbyPanel({ lat, lng }: Props) {
  const [data, setData]       = useState<NearbyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError('');
    fetch(`/api/nearby?lat=${lat}&lng=${lng}`)
      .then(r => r.json())
      .then(setData)
      .catch(() => setError('Could not load nearby amenities'))
      .finally(() => setLoading(false));
  }, [lat, lng]);

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

  if (error || !data) {
    return (
      <section className={styles.panel}>
        <div className={styles.header}>
          <h2 className={styles.title}>Nearby Amenities</h2>
        </div>
        <p className={styles.errorMsg}>Could not load nearby amenities at this time.</p>
      </section>
    );
  }

  const { places, summary } = data;
  const visiblePlaces = expanded ? places : places.slice(0, 5);

  return (
    <section className={styles.panel}>
      {/* ── Header ── */}
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
        <ConvenienceBadge score={summary.convenienceScore} />
      </div>

      {/* ── Summary stats row ── */}
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

      {/* ── Convenience callout ── */}
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

      {/* ── Place list ── */}
      {places.length === 0 ? (
        <p className={styles.noResults}>No GPs, dentists, pharmacies or shops found within {summary.radiusMiles} miles.</p>
      ) : (
        <>
          <ul className={styles.placeList}>
            {visiblePlaces.map(place => (
              <li key={place.id} className={styles.placeRow}>
                <div className={styles.placeIconWrap} data-type={place.type}>
                  <TypeIcon type={place.type} />
                </div>

                <div className={styles.placeInfo}>
                  <div className={styles.placeNameRow}>
                    <span className={styles.placeName}>{place.name}</span>
                    <span className={styles.typeChip}>{TYPE_LABELS[place.type]}</span>
                  </div>
                  {place.address && (
                    <p className={styles.placeAddress}>{place.address}</p>
                  )}
                </div>

                <div className={styles.placeDist}>
                  <span className={styles.distNum}>{formatDistance(place.distanceMiles)}</span>
                  <span className={styles.distWalk}>{walkMins(place.distanceMiles)} min walk</span>
                </div>
              </li>
            ))}
          </ul>

          {places.length > 5 && (
            <button
              className={styles.expandBtn}
              onClick={() => setExpanded(e => !e)}
            >
              {expanded
                ? 'Show fewer places'
                : `Show all ${places.length} nearby places`}
              <svg
                width="14" height="14" viewBox="0 0 14 14" fill="none"
                style={{ transform: expanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}
              >
                <path d="M2 5L7 9.5L12 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </button>
          )}
        </>
      )}
    </section>
  );
}
