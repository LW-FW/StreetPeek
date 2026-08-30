import { useEffect, useRef } from 'react';
import styles from './AreaMap.module.css';

interface MapPoint { lat:number; lng:number; type:'development'|'flood'|'conservation'|'crime'|'brownfield'; label:string; distance:string; }
interface AreaMapProps { lat:number; lng:number; points?:MapPoint[]; locked?:boolean; freeRadiusMiles?:number; }

const TYPE_COLOURS = { development:'#F26419', flood:'#378ADD', conservation:'#639922', crime:'#E24B4A', brownfield:'#BA7517' };
const TYPE_LABELS  = { development:'Development', flood:'Flood zone', conservation:'Conservation', crime:'Crime hotspot', brownfield:'Brownfield site' };
const toMetres = (miles:number) => miles * 1609.34;

export default function AreaMap({ lat, lng, points=[], locked=true, freeRadiusMiles=0.3 }: AreaMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);

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
      delete (L.Icon.Default.prototype as any)._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl:'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
        iconUrl:'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
        shadowUrl:'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
      });
      const map = L.map(containerRef.current!, { center:[lat,lng], zoom:locked?15:14, scrollWheelZoom:false });
      mapRef.current = map;
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>', maxZoom:19,
      }).addTo(map);
      const centreIcon = L.divIcon({ className:'', html:`<div style="width:14px;height:14px;border-radius:50%;background:#F26419;border:3px solid white;box-shadow:0 2px 6px rgba(242,100,25,0.5);"></div>`, iconSize:[14,14], iconAnchor:[7,7] });
      L.marker([lat,lng],{icon:centreIcon}).addTo(map).bindPopup('<strong>Search location</strong>');
      if (locked) L.circle([lat,lng],{radius:toMetres(freeRadiusMiles),color:'#F26419',weight:1.5,dashArray:'5 5',fillColor:'#F26419',fillOpacity:0.04}).addTo(map);
      const visible = locked ? points.filter(p => map.distance([lat,lng],[p.lat,p.lng]) <= toMetres(freeRadiusMiles)) : points;
      visible.forEach(point => {
        const colour = TYPE_COLOURS[point.type];
        const icon = L.divIcon({ className:'', html:`<div style="width:12px;height:12px;border-radius:50%;background:${colour};border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,0.25);"></div>`, iconSize:[12,12], iconAnchor:[6,6] });
        L.marker([point.lat,point.lng],{icon}).addTo(map).bindPopup(`<strong>${point.label}</strong><br/><span style="color:#888;font-size:12px;">${TYPE_LABELS[point.type]} · ${point.distance}</span>`);
      });
    });
    return () => {
      cancelled = true;
      if (mapRef.current) { mapRef.current.remove(); mapRef.current=null; }
    };
  }, [lat, lng]);

  return (
    <div className={styles.wrap}>
      <div ref={containerRef} className={styles.map} />
      <div className={styles.legend}>
        {Object.entries(TYPE_COLOURS).map(([type, colour]) => (
          <div key={type} className={`${styles.legendRow} ${locked && type==='crime' ? styles.locked : ''}`}>
            <span className={styles.legendDot} style={{background:colour}} />
            <span>{TYPE_LABELS[type as keyof typeof TYPE_LABELS]}</span>
            {locked && type==='crime' && <span className={styles.lockIcon}>locked</span>}
          </div>
        ))}
      </div>
      {locked && (
        <div className={styles.lockOverlay}>
          <div className={styles.lockCard}>
            <span className={styles.lockLabel}>Showing {freeRadiusMiles}mi radius</span>
            <a href="/pricing" className={styles.lockBtn}>Unlock 2mi view — £4.99</a>
          </div>
        </div>
      )}
    </div>
  );
}