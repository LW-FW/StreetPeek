// components/SchoolsPanel.tsx
// Drop this into your results page wherever you want the schools section.
//
// Usage in results.tsx:
//   import SchoolsPanel from '../components/SchoolsPanel';
//   ...
//   {location && <SchoolsPanel lat={location.lat} lng={location.lng} />}

import { useEffect, useState } from 'react';
import type { School, SchoolsResponse } from '../pages/api/schools';
import styles from '../styles/SchoolsPanel.module.css';

interface Props {
  lat: number;
  lng: number;
}

// ─── small helpers ────────────────────────────────────────────────────────────

function TrafficBadge({ risk }: { risk: 'low' | 'medium' | 'high' }) {
  const map = {
    low:    { label: 'Low traffic risk',    cls: styles.badgeLow },
    medium: { label: 'Medium traffic risk', cls: styles.badgeMedium },
    high:   { label: 'High traffic risk',   cls: styles.badgeHigh },
  };
  const { label, cls } = map[risk];
  return <span className={`${styles.badge} ${cls}`}>{label}</span>;
}

function OfstedPip({ rating }: { rating: 1 | 2 | 3 | 4 | null }) {
  if (!rating) return <span className={styles.pipNone} title="Not yet inspected">—</span>;
  const colours = ['', styles.pip1, styles.pip2, styles.pip3, styles.pip4];
  const labels  = ['', 'Outstanding', 'Good', 'Requires Improvement', 'Inadequate'];
  return (
    <span className={`${styles.pip} ${colours[rating]}`} title={labels[rating]}>
      {labels[rating]}
    </span>
  );
}

function TypeIcon({ type }: { type: School['type'] }) {
  if (type === 'nursery') {
    // baby/star icon
    return (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-label="Nursery">
        <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.4"/>
        <path d="M5.5 9.5C5.5 9.5 6.5 11 8 11C9.5 11 10.5 9.5 10.5 9.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
        <circle cx="6" cy="7" r="0.8" fill="currentColor"/>
        <circle cx="10" cy="7" r="0.8" fill="currentColor"/>
      </svg>
    );
  }
  if (type === 'secondary') {
    return (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-label="Secondary school">
        <rect x="2" y="6" width="12" height="8" rx="1" stroke="currentColor" strokeWidth="1.4"/>
        <path d="M5 6V4a3 3 0 0 1 6 0v2" stroke="currentColor" strokeWidth="1.4"/>
        <circle cx="8" cy="10" r="1.2" fill="currentColor"/>
      </svg>
    );
  }
  // primary / default
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-label="Primary school">
      <path d="M2 14V7L8 2L14 7V14" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/>
      <rect x="5.5" y="9" width="5" height="5" rx="0.5" stroke="currentColor" strokeWidth="1.2"/>
    </svg>
  );
}

function formatDistance(miles: number): string {
  if (miles < 0.1) return `${Math.round(miles * 1760)}yds`;
  return `${miles.toFixed(1)} mi`;
}

function walkMins(miles: number): number {
  // average walking speed ~3mph
  return Math.round((miles / 3) * 60);
}

// ─── main component ───────────────────────────────────────────────────────────

export default function SchoolsPanel({ lat, lng }: Props) {
  const [data, setData]       = useState<SchoolsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError('');
    fetch(`/api/schools?lat=${lat}&lng=${lng}`)
      .then(r => r.json())
      .then(setData)
      .catch(() => setError('Could not load school data'))
      .finally(() => setLoading(false));
  }, [lat, lng]);

  if (loading) {
    return (
      <section className={styles.panel}>
        <div className={styles.header}>
          <div className={styles.titleRow}>
            <span className={styles.titleIcon}>
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                <path d="M2 16V8L9 2L16 8V16" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/>
                <rect x="6" y="10" width="6" height="6" rx="0.5" stroke="currentColor" strokeWidth="1.4"/>
              </svg>
            </span>
            <h2 className={styles.title}>Schools &amp; Nurseries</h2>
          </div>
        </div>
        <div className={styles.loading}>
          <div className={styles.spinner} />
          <span>Finding nearby schools…</span>
        </div>
      </section>
    );
  }

  if (error || !data) {
    return (
      <section className={styles.panel}>
        <div className={styles.header}>
          <h2 className={styles.title}>Schools &amp; Nurseries</h2>
        </div>
        <p className={styles.errorMsg}>Could not load school data at this time.</p>
      </section>
    );
  }

  const { schools, summary } = data;
  const visibleSchools = expanded ? schools : schools.slice(0, 5);

  return (
    <section className={styles.panel}>
      {/* ── Header ── */}
      <div className={styles.header}>
        <div className={styles.titleRow}>
          <span className={styles.titleIcon}>
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M2 16V8L9 2L16 8V16" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/>
              <rect x="6" y="10" width="6" height="6" rx="0.5" stroke="currentColor" strokeWidth="1.4"/>
            </svg>
          </span>
          <h2 className={styles.title}>Schools &amp; Nurseries</h2>
        </div>
        <TrafficBadge risk={summary.trafficRisk} />
      </div>

      {/* ── Summary stats row ── */}
      <div className={styles.statsRow}>
        <div className={styles.stat}>
          <span className={styles.statNum}>{summary.totalSchools}</span>
          <span className={styles.statLabel}>Schools within 1mi</span>
        </div>
        <div className={styles.statDivider} />
        <div className={styles.stat}>
          <span className={styles.statNum}>{summary.totalNurseries}</span>
          <span className={styles.statLabel}>Nurseries within 1mi</span>
        </div>
        <div className={styles.statDivider} />
        <div className={styles.stat}>
          <span className={styles.statNum}>{summary.outstanding}</span>
          <span className={styles.statLabel}>Outstanding</span>
        </div>
        <div className={styles.statDivider} />
        <div className={styles.stat}>
          <span className={styles.statNum}>{summary.within400m}</span>
          <span className={styles.statLabel}>Within 400m</span>
        </div>
      </div>

      {/* ── Traffic risk callout ── */}
      <div className={`${styles.trafficCallout} ${styles[`traffic_${summary.trafficRisk}`]}`}>
        <span className={styles.trafficIcon}>
          {summary.trafficRisk === 'high' && '🚗'}
          {summary.trafficRisk === 'medium' && '⚠️'}
          {summary.trafficRisk === 'low' && '✅'}
        </span>
        <div>
          <span className={styles.trafficLabel}>School-run traffic</span>
          <p className={styles.trafficText}>{summary.trafficRiskReason}</p>
        </div>
      </div>

      {/* ── School list ── */}
      {schools.length === 0 ? (
        <p className={styles.noResults}>No schools or nurseries found within 1 mile.</p>
      ) : (
        <>
          <ul className={styles.schoolList}>
            {visibleSchools.map(school => (
              <li key={school.urn} className={styles.schoolRow}>
                <div className={styles.schoolIconWrap} data-type={school.type}>
                  <TypeIcon type={school.type} />
                </div>

                <div className={styles.schoolInfo}>
                  <div className={styles.schoolNameRow}>
                    <span className={styles.schoolName}>{school.name}</span>
                    <OfstedPip rating={school.ofstedRating} />
                  </div>
                  <div className={styles.schoolMeta}>
                    <span className={styles.metaChip}>{school.phase || school.type}</span>
                    {school.numberOfPupils && (
                      <span className={styles.metaChip}>{school.numberOfPupils.toLocaleString()} pupils</span>
                    )}
                    {school.capacityUtil !== null && (
                      <span className={`${styles.metaChip} ${school.capacityUtil > 95 ? styles.chipFull : ''}`}>
                        {school.capacityUtil}% full
                      </span>
                    )}
                  </div>
                  {school.address && (
                    <p className={styles.schoolAddress}>{school.address}</p>
                  )}
                </div>

                <div className={styles.schoolDist}>
                  <span className={styles.distNum}>{formatDistance(school.distanceMiles)}</span>
                  <span className={styles.distWalk}>{walkMins(school.distanceMiles)} min walk</span>
                </div>
              </li>
            ))}
          </ul>

          {schools.length > 5 && (
            <button
              className={styles.expandBtn}
              onClick={() => setExpanded(e => !e)}
            >
              {expanded
                ? 'Show fewer schools'
                : `Show all ${schools.length} schools & nurseries`}
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

      {/* ── Ofsted key ── */}
      <div className={styles.legend}>
        <span className={styles.legendLabel}>Ofsted:</span>
        {[
          { rating: 1 as const, label: 'Outstanding' },
          { rating: 2 as const, label: 'Good' },
          { rating: 3 as const, label: 'Requires improvement' },
          { rating: 4 as const, label: 'Inadequate' },
        ].map(({ rating, label }) => (
          <span key={rating} className={styles.legendItem}>
            <OfstedPip rating={rating} /> {label}
          </span>
        ))}
      </div>
    </section>
  );
}
