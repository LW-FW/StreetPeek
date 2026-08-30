// components/NearbyTab.tsx
// Full "Nearby" tab: category filters, radius toggle, a grouped list of
// GPs/dentists/pharmacies/supermarkets/shops/gyms split alongside a map.
//
// The API always fetches out to the max radius (2mi); filtering by a
// smaller radius or by category happens client-side against that one
// fetch, so toggling filters never re-hits the (rate-limited) Overpass API.
//
// `data` is fetched once by the parent Results page and passed in — this
// used to fetch on its own mount, which meant switching away from this tab
// and back unmounted/remounted it and re-hit Overpass every time.

import { useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import type { NearbyPlace, NearbyResponse } from '../pages/api/nearby';
import styles from './NearbyTab.module.css';

const NearbyMap = dynamic(() => import('./NearbyMap'), { ssr: false });

interface Props {
  lat: number;
  lng: number;
  data: NearbyResponse | null;
  loading: boolean;
  onRetry?: () => void;
}

const CATEGORY_ORDER: NearbyPlace['type'][] = ['gp', 'dentist', 'pharmacy', 'supermarket', 'convenience', 'gym'];

const CHIP_LABELS: Record<NearbyPlace['type'], string> = {
  gp: 'GP', dentist: 'Dentist', pharmacy: 'Pharmacy',
  supermarket: 'Supermarket', convenience: 'Shops', gym: 'Gym',
};
const SECTION_LABELS: Record<NearbyPlace['type'], string> = {
  gp: 'GPs', dentist: 'Dentists', pharmacy: 'Pharmacies',
  supermarket: 'Supermarkets', convenience: 'Shops', gym: 'Gyms & leisure centres',
};
const ICON_LABELS: Record<NearbyPlace['type'], string> = {
  gp: 'GP', dentist: 'D', pharmacy: 'Rx', supermarket: 'S', convenience: 'C', gym: 'Gy',
};

function formatDistance(miles: number): string {
  if (miles < 0.1) return `${Math.round(miles * 1760)}yds`;
  return `${miles.toFixed(2)}mi`;
}
function walkMins(miles: number): number {
  return Math.round((miles / 3) * 60);
}

export default function NearbyTab({ lat, lng, data, loading, onRetry }: Props) {
  const [activeCategories, setActiveCategories] = useState<Set<NearbyPlace['type']>>(
    new Set(CATEGORY_ORDER)
  );
  const [radiusMiles, setRadiusMiles] = useState<1 | 2>(2);

  const visiblePlaces = useMemo(() => {
    if (!data) return [];
    return data.places.filter(p => activeCategories.has(p.type) && p.distanceMiles <= radiusMiles);
  }, [data, activeCategories, radiusMiles]);

  const grouped = useMemo(() => {
    const groups = new Map<NearbyPlace['type'], NearbyPlace[]>();
    for (const type of CATEGORY_ORDER) groups.set(type, []);
    for (const p of visiblePlaces) groups.get(p.type)!.push(p);
    return groups;
  }, [visiblePlaces]);

  const countsByCategory = useMemo(() => {
    const counts = new Map<NearbyPlace['type'], number>();
    if (!data) return counts;
    for (const type of CATEGORY_ORDER) {
      counts.set(type, data.places.filter(p => p.type === type && p.distanceMiles <= radiusMiles).length);
    }
    return counts;
  }, [data, radiusMiles]);

  function toggleCategory(type: NearbyPlace['type']) {
    setActiveCategories(prev => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  }

  const allActive = activeCategories.size === CATEGORY_ORDER.length;

  if (loading) {
    return (
      <div className={styles.loading}>
        <div className={styles.spinner} />
        <span>Finding nearby GPs, dentists, shops and more…</span>
      </div>
    );
  }

  if (!data || !data.ok) {
    return (
      <div className={styles.errorState}>
        <p className={styles.errorMsg}>Couldn't reach nearby amenities data right now — the upstream map data source may be temporarily unavailable.</p>
        {onRetry && <button className={styles.retryBtn} onClick={onRetry}>Try again</button>}
      </div>
    );
  }

  return (
    <div>
      <div className={styles.filterRow}>
        <button
          className={`${styles.chip} ${styles.chipAll} ${allActive ? styles.chipAllOn : ''}`}
          onClick={() => setActiveCategories(new Set(CATEGORY_ORDER))}
        >
          All · {visiblePlaces.length}
        </button>
        {CATEGORY_ORDER.map(type => (
          <button
            key={type}
            className={`${styles.chip} ${styles[`cat_${type}`]} ${activeCategories.has(type) ? styles.chipOn : ''}`}
            onClick={() => toggleCategory(type)}
          >
            <span className={styles.dot} />
            {CHIP_LABELS[type]} <span className={styles.chipCount}>{countsByCategory.get(type) ?? 0}</span>
          </button>
        ))}
        <div className={styles.radiusToggle}>
          <button
            className={radiusMiles === 1 ? styles.radiusOn : ''}
            onClick={() => setRadiusMiles(1)}
          >1mi</button>
          <button
            className={radiusMiles === 2 ? styles.radiusOn : ''}
            onClick={() => setRadiusMiles(2)}
          >2mi</button>
        </div>
      </div>

      <div className={styles.splitWrap}>
        <div className={styles.splitList}>
          {visiblePlaces.length === 0 ? (
            <p className={styles.noResults}>No amenities found within {radiusMiles} {radiusMiles === 1 ? 'mile' : 'miles'} for the selected categories.</p>
          ) : (
            CATEGORY_ORDER.map(type => {
              const places = grouped.get(type) ?? [];
              if (places.length === 0) return null;
              return (
                <div key={type}>
                  <div className={styles.sectionLabel}>{SECTION_LABELS[type]}</div>
                  {places.map(place => (
                    <div key={place.id} className={`${styles.placeCard} ${styles[`cat_${type}`]}`}>
                      <div className={styles.placeIcon}>{ICON_LABELS[type]}</div>
                      <div className={styles.placeInfo}>
                        <div className={styles.placeName}>{place.name}</div>
                        {place.address && <div className={styles.placeMeta}>{place.address}</div>}
                      </div>
                      <div className={styles.placeDist}>
                        <span className={styles.placeDistNum}>{formatDistance(place.distanceMiles)}</span>
                        <span className={styles.placeDistWalk}>{walkMins(place.distanceMiles)} min walk</span>
                      </div>
                    </div>
                  ))}
                </div>
              );
            })
          )}
        </div>

        <div className={styles.splitMap}>
          <NearbyMap lat={lat} lng={lng} places={visiblePlaces} radiusMiles={radiusMiles} />
        </div>
      </div>
    </div>
  );
}
