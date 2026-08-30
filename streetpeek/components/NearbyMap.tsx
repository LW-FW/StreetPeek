import { useEffect, useRef } from 'react';
import type { NearbyPlace } from '../pages/api/nearby';
import styles from './NearbyMap.module.css';

interface NearbyMapProps {
  lat: number;
  lng: number;
  places: NearbyPlace[];
  radiusMiles: number;
}

const TYPE_COLOURS: Record<NearbyPlace['type'], string> = {
  gp: '#E24B4A',
  dentist: '#378ADD',
  pharmacy: '#639922',
  supermarket: '#F26419',
  convenience: '#BA7517',
  gym: '#888780',
};
const TYPE_LABELS: Record<NearbyPlace['type'], string> = {
  gp: 'GP',
  dentist: 'Dentist',
  pharmacy: 'Pharmacy',
  supermarket: 'Supermarket',
  convenience: 'Shop',
  gym: 'Gym / leisure',
};

const toMetres = (miles: number) => miles * 1609.34;

// Base map (tiles, centre marker, radius circle) is created once per lat/lng.
// Category markers live in their own layer group that gets rebuilt whenever
// the filtered `places` list changes, so toggling a filter chip doesn't
// re-init the whole map (which would flash and reset zoom/pan).
export default function NearbyMap({ lat, lng, places, radiusMiles }: NearbyMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const markersLayerRef = useRef<any>(null);
  const circleRef = useRef<any>(null);
  const leafletRef = useRef<any>(null);

  useEffect(() => {
    if (typeof window === 'undefined' || !containerRef.current) return;
    // React Strict Mode runs this effect, its cleanup, then this effect again
    // in dev — since the leaflet import is async, both runs can still be
    // in-flight when the first one's cleanup fires. `cancelled` lets a stale
    // run recognise it's been superseded instead of initialising a second
    // map on the same (already-bound) DOM node.
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
    });
    return () => {
      cancelled = true;
      if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; }
    };
  }, [lat, lng]);

  // Rebuild the radius circle and category markers when the filtered list changes.
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

    places.forEach(place => {
      const colour = TYPE_COLOURS[place.type];
      const icon = L.divIcon({
        className: '',
        html: `<div style="width:12px;height:12px;border-radius:50%;background:${colour};border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,0.25);"></div>`,
        iconSize: [12, 12], iconAnchor: [6, 6],
      });
      L.marker([place.lat, place.lng], { icon })
        .addTo(markersLayerRef.current)
        .bindPopup(`<strong>${place.name}</strong><br/><span style="color:#888;font-size:12px;">${TYPE_LABELS[place.type]} · ${place.distanceMiles.toFixed(2)}mi</span>`);
    });
  }, [places, radiusMiles, lat, lng]);

  return (
    <div className={styles.wrap}>
      <div ref={containerRef} className={styles.map} />
      <div className={styles.legend}>
        {(Object.keys(TYPE_COLOURS) as NearbyPlace['type'][]).map(type => (
          <div key={type} className={styles.legendRow}>
            <span className={styles.legendDot} style={{ background: TYPE_COLOURS[type] }} />
            <span>{TYPE_LABELS[type]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
