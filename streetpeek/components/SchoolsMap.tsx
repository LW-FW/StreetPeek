// components/SchoolsMap.tsx
// Leaflet map for the Schools tab — same base-map/markers-layer split as
// NearbyMap.tsx, plus a selection concept NearbyMap doesn't need: clicking
// a row in SchoolsTab's list highlights the matching pin here (and vice
// versa), so markers are tracked in a ref keyed by item id.

import { useEffect, useRef, useState } from 'react';
import styles from './SchoolsMap.module.css';

export interface SchoolsMapItem {
  id: string;
  name: string;
  lat: number;
  lng: number;
  distanceMiles: number;
  group: 'primary' | 'secondary' | 'nursery';
}

interface SchoolsMapProps {
  lat: number;
  lng: number;
  items: SchoolsMapItem[];
  radiusMiles: number;
  selectedId: string | null;
  onSelect: (id: string) => void;
}

const GROUP_COLOURS: Record<SchoolsMapItem['group'], string> = {
  primary: '#4f46e5',
  secondary: '#0891b2',
  nursery: '#b45309',
};
const GROUP_LABELS: Record<SchoolsMapItem['group'], string> = {
  primary: 'Primary school',
  secondary: 'Secondary school',
  nursery: 'Nursery',
};

const toMetres = (miles: number) => miles * 1609.34;

function pinIcon(L: any, colour: string, selected: boolean) {
  const size = selected ? 20 : 12;
  const border = selected ? 3 : 2;
  return L.divIcon({
    className: '',
    html: `<div style="width:${size}px;height:${size}px;border-radius:50%;background:${colour};border:${border}px solid white;box-shadow:0 ${selected ? 2 : 1}px ${selected ? 10 : 4}px rgba(0,0,0,${selected ? 0.35 : 0.25});"></div>`,
    iconSize: [size, size], iconAnchor: [size / 2, size / 2],
  });
}

export default function SchoolsMap({ lat, lng, items, radiusMiles, selectedId, onSelect }: SchoolsMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const markersLayerRef = useRef<any>(null);
  const markerRefsRef = useRef<Record<string, any>>({});
  const circleRef = useRef<any>(null);
  const leafletRef = useRef<any>(null);
  // Plain refs (mapRef/leafletRef) don't trigger a re-run of the markers
  // effect below when the async `import('leaflet')` resolves — that effect
  // fires once on mount, sees the map isn't built yet, and bails out; since
  // its own deps (items/radiusMiles/lat/lng) don't necessarily change again
  // afterward, it would never retry and the pins would silently never
  // appear. `ready` is real React state so becoming true forces that retry.
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined' || !containerRef.current) return;
    let cancelled = false;

    import('leaflet').then(L => {
      if (cancelled || !containerRef.current || (containerRef.current as any)._leaflet_id) return;
      leafletRef.current = L;
      delete (L.Icon.Default.prototype as any)._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
        iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
        shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
      });
      const map = L.map(containerRef.current!, { center: [lat, lng], zoom: 14, scrollWheelZoom: false });
      mapRef.current = map;
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
      }).addTo(map);

      const centreIcon = L.divIcon({
        className: '',
        html: `<div style="width:14px;height:14px;border-radius:50%;background:#F26419;border:3px solid white;box-shadow:0 2px 6px rgba(242,100,25,0.5);"></div>`,
        iconSize: [14, 14], iconAnchor: [7, 7],
      });
      L.marker([lat, lng], { icon: centreIcon }).addTo(map).bindPopup('<strong>Search location</strong>');

      markersLayerRef.current = L.layerGroup().addTo(map);
      setReady(true);
    });
    return () => {
      cancelled = true;
      if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; }
      setReady(false);
    };
  }, [lat, lng]);

  // Rebuild the radius circle and markers when the filtered list changes.
  useEffect(() => {
    const L = leafletRef.current;
    const map = mapRef.current;
    if (!L || !map) return;

    if (circleRef.current) circleRef.current.remove();
    circleRef.current = L.circle([lat, lng], {
      radius: toMetres(radiusMiles), color: '#F26419', weight: 1.5, dashArray: '5 5',
      fillColor: '#F26419', fillOpacity: 0.03,
    }).addTo(map);

    if (markersLayerRef.current) markersLayerRef.current.clearLayers();
    else markersLayerRef.current = L.layerGroup().addTo(map);
    markerRefsRef.current = {};

    items.forEach(item => {
      const colour = GROUP_COLOURS[item.group];
      const marker = L.marker([item.lat, item.lng], { icon: pinIcon(L, colour, item.id === selectedId) })
        .addTo(markersLayerRef.current)
        .bindPopup(`<strong>${item.name}</strong><br/><span style="color:#888;font-size:12px;">${GROUP_LABELS[item.group]} · ${item.distanceMiles.toFixed(2)}mi</span>`)
        .on('click', () => onSelect(item.id));
      markerRefsRef.current[item.id] = marker;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items, radiusMiles, lat, lng, ready]);

  // Re-style + pan to whichever item is selected from the list.
  useEffect(() => {
    const L = leafletRef.current;
    const map = mapRef.current;
    if (!L || !map) return;

    items.forEach(item => {
      const marker = markerRefsRef.current[item.id];
      if (!marker) return;
      marker.setIcon(pinIcon(L, GROUP_COLOURS[item.group], item.id === selectedId));
    });

    if (selectedId) {
      const marker = markerRefsRef.current[selectedId];
      if (marker) {
        map.panTo(marker.getLatLng());
        marker.openPopup();
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId, ready]);

  return (
    <div className={styles.wrap}>
      <div ref={containerRef} className={styles.map} />
      <div className={styles.legend}>
        {(Object.keys(GROUP_COLOURS) as SchoolsMapItem['group'][]).map(group => (
          <div key={group} className={styles.legendRow}>
            <span className={styles.legendDot} style={{ background: GROUP_COLOURS[group] }} />
            <span>{GROUP_LABELS[group]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
