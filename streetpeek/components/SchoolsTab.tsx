// components/SchoolsTab.tsx
// Full "Schools" tab: category filters, radius toggle, a grouped list of
// nurseries/primary/secondary schools split alongside a map — same split
// layout as NearbyTab.tsx, plus click-to-locate: selecting a row highlights
// its pin on the map (and vice versa).
//
// The API always fetches out to the max radius (2mi); filtering by a
// smaller radius happens client-side against that one fetch, matching
// NearbyTab's convention, so toggling the radius never re-hits the API.
//
// `data` is fetched once by the parent Results page and passed in — same
// reasoning as NearbyTab: fetching per-mount would re-hit the API (and
// re-parse the multi-MB local dataset) every time this tab is switched to.

import { useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import type { EducationResponse, SchoolResult, NurseryResult } from '../pages/api/schools';
import { schoolRatingPill, nurseryRatingPill, phaseGroup, type PhaseGroup } from '../lib/schoolRatings';
import styles from './SchoolsTab.module.css';

const SchoolsMap = dynamic(() => import('./SchoolsMap'), { ssr: false });

interface Props {
  lat: number;
  lng: number;
  data: EducationResponse | null;
  loading: boolean;
  onRetry?: () => void;
}

type Item = (SchoolResult | NurseryResult) & { group: PhaseGroup; kind: 'school' | 'nursery' };

const FILTER_ORDER: Array<{ key: PhaseGroup | 'all'; label: string }> = [
  { key: 'all', label: 'All' },
  { key: 'nursery', label: 'Nurseries' },
  { key: 'primary', label: 'Primary' },
  { key: 'secondary', label: 'Secondary' },
];
const GROUP_SECTION_LABEL: Record<PhaseGroup, string> = {
  nursery: 'Nurseries', primary: 'Primary schools', secondary: 'Secondary schools',
};

function formatDistance(miles: number): string {
  if (miles < 0.1) return `${Math.round(miles * 1760)}yds`;
  return `${miles.toFixed(2)}mi`;
}

export default function SchoolsTab({ lat, lng, data, loading, onRetry }: Props) {
  const [activeFilter, setActiveFilter] = useState<PhaseGroup | 'all'>('all');
  const [radiusMiles, setRadiusMiles] = useState<1 | 2>(2);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const items: Item[] = useMemo(() => {
    if (!data) return [];
    const schools: Item[] = data.schools.map(s => ({ ...s, group: phaseGroup(s.phase), kind: 'school' as const }));
    const nurseries: Item[] = data.nurseries.map(n => ({ ...n, group: 'nursery' as PhaseGroup, kind: 'nursery' as const }));
    return [...schools, ...nurseries].sort((a, b) => a.distanceMiles - b.distanceMiles);
  }, [data]);

  const visibleItems = useMemo(() => {
    return items.filter(item =>
      item.distanceMiles <= radiusMiles && (activeFilter === 'all' || item.group === activeFilter)
    );
  }, [items, activeFilter, radiusMiles]);

  const grouped = useMemo(() => {
    const groups: Record<PhaseGroup, Item[]> = { nursery: [], primary: [], secondary: [] };
    for (const item of visibleItems) groups[item.group].push(item);
    return groups;
  }, [visibleItems]);

  const countsByFilter = useMemo(() => {
    const inRadius = items.filter(i => i.distanceMiles <= radiusMiles);
    return {
      all: inRadius.length,
      nursery: inRadius.filter(i => i.group === 'nursery').length,
      primary: inRadius.filter(i => i.group === 'primary').length,
      secondary: inRadius.filter(i => i.group === 'secondary').length,
    };
  }, [items, radiusMiles]);

  const mapItems = useMemo(() => visibleItems.map(item => ({
    id: item.id, name: item.name, lat: item.lat, lng: item.lng, distanceMiles: item.distanceMiles, group: item.group,
  })), [visibleItems]);

  if (loading) {
    return (
      <div className={styles.loading}>
        <div className={styles.spinner} />
        <span>Finding nearby schools and nurseries…</span>
      </div>
    );
  }

  if (!data) {
    return (
      <div className={styles.errorState}>
        <p className={styles.errorMsg}>Couldn&apos;t reach school data right now.</p>
        {onRetry && <button className={styles.retryBtn} onClick={onRetry}>Try again</button>}
      </div>
    );
  }

  return (
    <div>
      <div className={styles.topBanner}>
        <span>🔄</span>
        <span>
          <strong>Ofsted is partway through replacing the old single grade with a category-by-category &quot;report card&quot;</strong> — each school below shows whichever one it last received, so you&apos;ll see a mix. Nurseries stay on the old single-grade scale and <strong>refresh monthly</strong>. Only registered nurseries &amp; preschools are shown here, not childminders or out-of-school clubs.
        </span>
      </div>

      <div className={styles.filterRow}>
        {FILTER_ORDER.map(f => (
          <button
            key={f.key}
            className={`${styles.filterChip} ${activeFilter === f.key ? styles.filterChipOn : ''}`}
            onClick={() => setActiveFilter(f.key)}
          >
            {f.label} <span className={styles.filterCount}>{countsByFilter[f.key]}</span>
          </button>
        ))}
        <div className={styles.radiusToggle}>
          <button className={radiusMiles === 1 ? styles.radiusOn : ''} onClick={() => setRadiusMiles(1)}>1mi</button>
          <button className={radiusMiles === 2 ? styles.radiusOn : ''} onClick={() => setRadiusMiles(2)}>2mi</button>
        </div>
      </div>

      <div className={styles.splitWrap}>
        <div className={styles.splitList}>
          {visibleItems.length === 0 ? (
            <p className={styles.noResults}>No schools or nurseries found within {radiusMiles} {radiusMiles === 1 ? 'mile' : 'miles'} for the selected filter.</p>
          ) : (
            (['nursery', 'primary', 'secondary'] as PhaseGroup[]).map(group => {
              const groupItems = grouped[group];
              if (groupItems.length === 0) return null;
              return (
                <div key={group}>
                  <div className={styles.sectionLabel}>
                    {GROUP_SECTION_LABEL[group]}
                    {group === 'nursery' && <span className={styles.sectionNote}>registered only</span>}
                  </div>
                  {groupItems.map(item => {
                    const pill = item.kind === 'nursery'
                      ? nurseryRatingPill((item as NurseryResult).rating.grade)
                      : schoolRatingPill((item as SchoolResult).rating);
                    return (
                      <div
                        key={item.id}
                        className={`${styles.row} ${item.id === selectedId ? styles.rowSelected : ''}`}
                        onClick={() => setSelectedId(prev => prev === item.id ? null : item.id)}
                      >
                        <div className={`${styles.rowIcon} ${styles[`icon_${group}`]}`}>
                          {group === 'secondary' ? 'S' : group === 'primary' ? 'P' : 'N'}
                        </div>
                        <div className={styles.rowInfo}>
                          <span className={styles.rowName}>{item.name}</span>
                          <span className={`${styles.gradePill} ${pill.grade ? styles[`g${pill.grade}`] : styles.gradeNeutral}`}>{pill.text}</span>
                        </div>
                        <span className={styles.rowDist}>{formatDistance(item.distanceMiles)}</span>
                      </div>
                    );
                  })}
                </div>
              );
            })
          )}
        </div>

        <div className={styles.splitMap}>
          <SchoolsMap lat={lat} lng={lng} items={mapItems} radiusMiles={radiusMiles} selectedId={selectedId} onSelect={id => setSelectedId(prev => prev === id ? null : id)} />
        </div>
      </div>
    </div>
  );
}
