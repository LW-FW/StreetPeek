import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import Head from 'next/head';
import Navbar from '../components/Navbar';
import Badge from '../components/Badge';
import { IconWaves,IconShield,IconHouse,IconMap,IconTick,IconCross,IconCrime,IconAlert,IconDocument,IconCalendar } from '../components/icons';
import { lookupPostcode,getCrimeData,getPlanningData,getEnvironmentalData,computeAreaScore,parsePoint,distanceMiles,formatDistance,PostcodeData,CrimeData,PlanningEntity } from '../lib/data';
import styles from '../styles/Results.module.css';
import SchoolsSummary from '../components/SchoolsSummary';
import SchoolsTab from '../components/SchoolsTab';
import NearbyTab from '../components/NearbyTab';
import NearbySummary from '../components/NearbySummary';
import type { NearbyResponse } from './api/nearby';
import type { EducationResponse } from './api/schools';

const AreaMap = dynamic(() => import('../components/AreaMap'), { ssr: false });
type Tab = 'overview'|'nearby'|'schools'|'planning'|'crime'|'environment'|'map';

export default function Results() {
  const router = useRouter();
  const postcode = (router.query.postcode as string || '').toUpperCase();
  const [tab, setTab] = useState<Tab>('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [location, setLocation] = useState<PostcodeData|null>(null);
  const [crimeData, setCrimeData] = useState<CrimeData[]>([]);
  const [planningData, setPlanningData] = useState<PlanningEntity[]>([]);
  const [envData, setEnvData] = useState<PlanningEntity[]>([]);
  const [nearbyData, setNearbyData] = useState<NearbyResponse|null>(null);
  const [nearbyLoading, setNearbyLoading] = useState(true);
  const [schoolsData, setSchoolsData] = useState<EducationResponse|null>(null);
  const [schoolsLoading, setSchoolsLoading] = useState(true);

  useEffect(() => {
    if (!postcode) return;
    setLoading(true); setError('');
    async function load() {
      try {
        const loc = await lookupPostcode(postcode);
        setLocation(loc);
        const [crime,planning,env] = await Promise.all([getCrimeData(loc.lat,loc.lng),getPlanningData(loc.lat,loc.lng),getEnvironmentalData(loc.lat,loc.lng)]);
        setCrimeData(crime); setPlanningData(planning); setEnvData(env);
      } catch(e:any) { setError(e.message||'Could not load data for this postcode'); }
      finally { setLoading(false); }
    }
    load();
  }, [postcode]);

  // Fetched once per postcode by this always-mounted parent, not by the tab
  // content itself — NearbySummary/NearbyTab used to fetch on their own
  // mount, so switching tabs unmounted+remounted them and re-hit the
  // (rate-limited, sometimes-flaky) Overpass API on every visit.
  const loadNearby = () => {
    if (!location) return;
    setNearbyLoading(true);
    fetch(`/api/nearby?lat=${location.lat}&lng=${location.lng}`)
      .then(r => r.json())
      .then(setNearbyData)
      .catch(() => setNearbyData(null))
      .finally(() => setNearbyLoading(false));
  };
  useEffect(loadNearby, [location?.lat, location?.lng]);

  const loadSchools = () => {
    if (!location) return;
    setSchoolsLoading(true);
    fetch(`/api/schools?lat=${location.lat}&lng=${location.lng}`)
      .then(r => r.json())
      .then(setSchoolsData)
      .catch(() => setSchoolsData(null))
      .finally(() => setSchoolsLoading(false));
  };
  useEffect(loadSchools, [location?.lat, location?.lng]);

  if (!postcode) return <div className={styles.page}><Navbar /><p className={styles.empty}>No postcode provided.</p></div>;

  const {score,label} = location ? computeAreaScore(crimeData,planningData,envData) : {score:0,label:''};
  const totalCrime = crimeData.reduce((s,c)=>s+c.count,0);
  const maxCrime = Math.max(...crimeData.map(c=>c.count),1);
  const brownfield = planningData.filter(e=>e.dataset==='brownfield-land');
  const applications = planningData.filter(e=>e.dataset==='planning-application');
  const hasFlood = envData.some(e=>e.dataset==='flood-risk-zone');
  const hasConservation = envData.some(e=>e.dataset==='conservation-area');
  const hasGreenBelt = envData.some(e=>e.dataset==='green-belt');
  const hasListedBuildings = envData.some(e=>e.dataset==='listed-building');
  const hasAncientWoodland = envData.some(e=>e.dataset==='ancient-woodland');
  const hasSSI = envData.some(e=>e.dataset==='site-of-special-scientific-interest');

  const mapPoints = planningData.flatMap(e=>{
    const p=parsePoint(e.point||'');
    if (!p||!location) return [];
    const dist=distanceMiles(location.lat,location.lng,p.lat,p.lng);
    return [{lat:p.lat,lng:p.lng,type:(e.dataset==='flood-risk-zone'?'flood':e.dataset==='conservation-area'?'conservation':'development') as any,label:e.name||e.dataset,distance:formatDistance(dist)}];
  });

  return (
    <>
      <Head><title>{postcode} area report — StreetPeek</title></Head>
      <div className={styles.page}>
        <Navbar />
        {loading && <div className={styles.loadingWrap}><div className={styles.spinner}/><p>Looking up {postcode}…</p></div>}
        {error && <div className={styles.errorWrap}><IconAlert size={24} color="var(--red)"/><p>{error}</p></div>}
        {!loading && !error && location && (<>
          <div className={styles.header}>
            <h1 className={styles.postcode}>{location.postcode}</h1>
            <p className={styles.areaName}>{[location.ward,location.admin_district].filter(Boolean).join(', ')}</p>
          </div>

          <div className={styles.summaryWrap}>
            <div className={styles.summary}>
              <div className={styles.summaryLabel}>Area summary</div>
              <div className={styles.outlookRow}>
                <div className={styles.score}><span className={styles.scoreNum}>{score.toFixed(1)}</span><span className={styles.scoreTag}>{label}</span></div>
              </div>
              <p>
                {location.admin_district} —
                {brownfield.length>0?` ${brownfield.length} brownfield site${brownfield.length>1?'s':''} with housing development within 1 mile.`:' No brownfield housing sites found within 1 mile.'}
                {totalCrime>0?` ${totalCrime} crimes recorded in the last available month.`:''}
                {hasFlood?' Flood risk zones present nearby — check before buying.':' No flood risk zones detected.'}
                {hasConservation?' Area is within or near a conservation zone.':''}
              </p>
              <a href="/data-sources" className={styles.methodLink}>Understand how we calculate your report and any limitations of the data →</a>
            </div>
          </div>

          <div className={styles.tabs}>
            {([
              {id:'overview',icon:'🏠',label:'Overview'},
              {id:'nearby',icon:'📍',label:'Nearby'},
              {id:'schools',icon:'🏫',label:'Schools'},
              {id:'planning',icon:'🏠',label:'Planning'},
              {id:'crime',icon:'🚨',label:'Crime'},
              {id:'environment',icon:'🌊',label:'Environment'},
              {id:'map',icon:'🗺',label:'Map view'},
            ] as {id:Tab;icon:React.ReactNode;label:string}[]).map(t=>(
              <button key={t.id} className={`${styles.tab} ${tab===t.id?styles.tabActive:''}`} onClick={()=>setTab(t.id)}>
                {t.icon} {t.label}
              </button>
            ))}
          </div>

          {tab==='overview' && (
            <div className={styles.panelWrap}>
            <div className={styles.panel}>
              <div className={styles.grid}>
                <div className={styles.card}>
                  <div className={styles.cardHeader}>
                    <div className={styles.cardTitle}>🏠 Housing developments</div>
                    <Badge variant={brownfield.length>0?'orange':'neutral'}>{brownfield.length>0?'Active':'None found'}</Badge>
                  </div>
                  <div className={styles.bigNum}>{brownfield.length}</div>
                  <div className={styles.bigSub}>brownfield sites within search radius</div>
                  {brownfield.length>0&&<p className={styles.cardNote}>Up to {brownfield.reduce((s,e)=>s+parseInt(e.maximum_net_dwellings||'0'),0)} homes across all sites</p>}
                </div>
                <div className={styles.card}>
                  <div className={styles.cardHeader}>
                    <div className={styles.cardTitle}>🚨 Crime this month</div>
                    <Badge variant={totalCrime<50?'good':totalCrime<150?'warn':'red'}>{totalCrime<50?'Low':totalCrime<150?'Moderate':'High'}</Badge>
                  </div>
                  <div className={styles.bigNum}>{totalCrime}</div>
                  <div className={styles.bigSub}>crimes recorded</div>
                  <div className={styles.bars}>
                    {crimeData.slice(0,4).map(c=>(
                      <div key={c.category} className={styles.barRow}>
                        <span className={styles.barLabel}>{c.category}</span>
                        <div className={styles.barTrack}><div className={styles.barFill} style={{width:`${(c.count/maxCrime)*100}%`,background:'#FAC775'}}/></div>
                        <span className={styles.barVal}>{c.count}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className={styles.card}>
                  <div className={styles.cardHeader}>
                    <div className={styles.cardTitle}>🌊 Flood risk</div>
                    <Badge variant={hasFlood?'warn':'good'}>{hasFlood?'Risk present':'Low risk'}</Badge>
                  </div>
                  <CheckRow ok={!hasFlood}>{hasFlood?'Flood risk zone detected nearby':'No flood risk zones nearby'}</CheckRow>
                </div>
                <div className={styles.card}>
                  <div className={styles.cardHeader}>
                    <div className={styles.cardTitle}>🛡️ Area protections</div>
                    <Badge variant={hasConservation||hasGreenBelt?'info':'neutral'}>{hasConservation||hasGreenBelt?'Protected':'Unrestricted'}</Badge>
                  </div>
                  <CheckRow ok={!hasConservation} neutral>Conservation area: {hasConservation?'Yes':'No'}</CheckRow>
                  <CheckRow ok={!hasGreenBelt} neutral>Green belt: {hasGreenBelt?'Yes':'No'}</CheckRow>
                  <CheckRow ok={!hasListedBuildings} neutral>Listed buildings: {hasListedBuildings?'Nearby':'None nearby'}</CheckRow>
                </div>
                {brownfield.length>0&&(
                  <div className={`${styles.card} ${styles.full}`}>
                    <div className={styles.cardHeader}>
                      <div className={styles.cardTitle}>🏠 Nearby sites</div>
                      <Badge variant="orange">{brownfield.length} sites</Badge>
                    </div>
                    {brownfield.slice(0,4).map((e,i)=>{
                      const pt=parsePoint(e.point||'');
                      const dist=pt&&location?formatDistance(distanceMiles(location.lat,location.lng,pt.lat,pt.lng)):'—';
                      const maxD=parseInt(e.maximum_net_dwellings||'0');
                      return (
                        <div key={i} className={styles.devItem}>
                          <div className={styles.devIcon} style={{background:'var(--orange-light)'}}>🏠</div>
                          <div style={{flex:1}}>
                            <p className={styles.devTitle}>{e.name||'Unnamed site'}</p>
                            <p className={styles.devMeta}>{maxD>0?`Up to ${maxD} homes`:'Homes TBC'}{dist!=='—'?` · ${dist} away`:''}{e.hectares?` · ${e.hectares} ha`:''}</p>
                          </div>
                          <Badge variant={e.planning_permission_status==='permissioned'?'good':'warn'}>{e.planning_permission_status==='permissioned'?'Approved':e.planning_permission_status||'Unknown'}</Badge>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* ── Schools & Nurseries summary (full detail in the Schools tab) ── */}
              <SchoolsSummary data={schoolsData} loading={schoolsLoading} onViewAll={() => setTab('schools')} onRetry={loadSchools} />

              {/* ── Nearby Amenities summary (full detail in the Nearby tab) ── */}
              <NearbySummary data={nearbyData} loading={nearbyLoading} onViewAll={() => setTab('nearby')} onRetry={loadNearby} />

              <UnlockBanner />
            </div>
            </div>
          )}

          {tab==='nearby' && (
            <div className={styles.panelWrap}>
            <div className={styles.panel}>
              <NearbyTab lat={location.lat} lng={location.lng} data={nearbyData} loading={nearbyLoading} onRetry={loadNearby} />
            </div>
            </div>
          )}

          {tab==='schools' && (
            <div className={styles.panelWrap}>
            <div className={styles.panel}>
              <SchoolsTab lat={location.lat} lng={location.lng} data={schoolsData} loading={schoolsLoading} onRetry={loadSchools} />
            </div>
            </div>
          )}

          {tab==='planning' && (
            <div className={styles.panelWrap}>
            <div className={styles.panel}>
              <p className={styles.tabIntro}><IconDocument size={15} color="var(--orange)"/>&nbsp;Showing free preview — {Math.min(brownfield.length+applications.length,3)} of {brownfield.length+applications.length} results.{' '}<a href="/pricing" className={styles.orangeLink}>Unlock all →</a></p>
              <div className={styles.card} style={{marginBottom:'1rem'}}>
                {[...brownfield,...applications].slice(0,3).map((e,i)=>{
                  const pt=parsePoint(e.point||'');
                  const dist=pt&&location?formatDistance(distanceMiles(location.lat,location.lng,pt.lat,pt.lng)):null;
                  return (
                    <div key={i} className={styles.devItem}>
                      <div className={styles.devIcon} style={{background:'var(--orange-light)'}}><IconHouse size={15} color="var(--orange)"/></div>
                      <div style={{flex:1}}>
                        <p className={styles.devTitle}>{e.name||'Planning application'}</p>
                        <p className={styles.devMeta}>{e.dataset} · {e.start_date||'Date unknown'}{dist?` · ${dist} away`:''}</p>
                      </div>
                      <Badge variant={e.planning_permission_status==='permissioned'?'good':'neutral'}>{e.planning_permission_status||'Unknown'}</Badge>
                    </div>
                  );
                })}
                {brownfield.length+applications.length===0&&<p className={styles.emptyMsg}>No planning applications found. Coverage varies by council.</p>}
              </div>
              <UnlockBanner />
            </div>
            </div>
          )}

          {tab==='crime' && (
            <div className={styles.panelWrap}>
            <div className={styles.panel}>
              <div className={styles.card}>
                <div className={styles.cardHeader}>
                  <div className={styles.cardTitle}><IconCrime size={15} color="var(--amber)"/> Crime by category</div>
                  <Badge variant={totalCrime<50?'good':totalCrime<150?'warn':'red'}>{totalCrime} total</Badge>
                </div>
                {crimeData.length===0&&<p className={styles.emptyMsg}>No crime data available for this area.</p>}
                {crimeData.map(c=>(
                  <div key={c.category} className={styles.barRow} style={{marginBottom:'10px'}}>
                    <span className={styles.barLabel}>{c.category}</span>
                    <div className={styles.barTrack}><div className={styles.barFill} style={{width:`${(c.count/maxCrime)*100}%`,background:'#FAC775'}}/></div>
                    <span className={styles.barVal}>{c.count}</span>
                  </div>
                ))}
                <p className={styles.dataSource}><IconCalendar size={13} color="var(--text-tertiary)"/> Source: data.police.uk · 3-year trend charts in full report</p>
              </div>
              <UnlockBanner />
            </div>
            </div>
          )}

          {tab==='environment' && (
            <div className={styles.panelWrap}>
            <div className={styles.panel}>
              <div className={styles.grid}>
                <div className={styles.card}>
                  <div className={styles.cardHeader}><div className={styles.cardTitle}><IconWaves size={15} color="var(--blue)"/> Flood risk</div><Badge variant={hasFlood?'warn':'good'}>{hasFlood?'Risk present':'Low risk'}</Badge></div>
                  <CheckRow ok={!hasFlood}>{hasFlood?'Flood risk zone present':'No flood risk zones within radius'}</CheckRow>
                </div>
                <div className={styles.card}>
                  <div className={styles.cardHeader}><div className={styles.cardTitle}><IconShield size={15} color="var(--gray)"/> Designations</div></div>
                  <CheckRow ok={!hasConservation} neutral>Conservation area: {hasConservation?'Yes':'No'}</CheckRow>
                  <CheckRow ok={!hasGreenBelt} neutral>Green belt: {hasGreenBelt?'Yes':'No'}</CheckRow>
                  <CheckRow ok={!hasAncientWoodland} neutral>Ancient woodland: {hasAncientWoodland?'Yes':'No'}</CheckRow>
                  <CheckRow ok={!hasSSI} neutral>SSSI: {hasSSI?'Yes':'No'}</CheckRow>
                  <CheckRow ok={!hasListedBuildings} neutral>Listed buildings: {hasListedBuildings?'Nearby':'None nearby'}</CheckRow>
                </div>
              </div>
              <UnlockBanner />
            </div>
            </div>
          )}

          {tab==='map' && (
            <div className={styles.panelWrap}>
            <div className={styles.panel}>
              <p className={styles.tabIntro}><IconMap size={15} color="var(--orange)"/>&nbsp;Free view: 0.3 mile radius. <a href="/pricing" className={styles.orangeLink}>Unlock 2-mile view →</a></p>
              <AreaMap lat={location.lat} lng={location.lng} points={mapPoints} locked={true} freeRadiusMiles={0.3}/>
            </div>
            </div>
          )}
        </>)}
      </div>
    </>
  );
}

function CheckRow({ok,neutral=false,children}:{ok?:boolean;neutral?:boolean;children:React.ReactNode}) {
  return (
    <div style={{display:'flex',alignItems:'flex-start',gap:10,padding:'7px 0',borderBottom:'0.5px solid var(--border)'}}>
      {ok ? <IconTick size={18} color="var(--green)"/> : <IconCross size={18} color={neutral?'var(--gray)':'var(--amber)'}/>}
      <span style={{fontSize:13,lineHeight:1.4}}>{children}</span>
    </div>
  );
}

function UnlockBanner() {
  return (
    <div style={{marginTop:'1.5rem',padding:'1.25rem',border:'0.5px solid var(--border-mid)',borderRadius:'var(--radius-lg)',background:'var(--bg-secondary)',textAlign:'center'}}>
      <h4 style={{fontSize:14,fontWeight:500,marginBottom:6}}>Get the full picture</h4>
      <p style={{fontSize:13,color:'var(--text-secondary)',marginBottom:14,lineHeight:1.55}}>Unlock all planning applications with reference numbers, 3-year crime charts, a 2-mile map with every data layer, and a PDF to share with your solicitor.</p>
      <div style={{display:'flex',flexWrap:'wrap',gap:6,justifyContent:'center',marginBottom:14}}>
        {['All planning docs','3-year crime charts','2mi map view','PDF report','Email alerts'].map(f=>(
          <span key={f} style={{fontSize:12,background:'var(--bg)',border:'0.5px solid var(--border)',borderRadius:'999px',padding:'4px 12px',color:'var(--text-secondary)'}}>{f}</span>
        ))}
      </div>
      <a href="/pricing" style={{display:'inline-block',background:'var(--orange)',color:'white',border:'none',borderRadius:'var(--radius-md)',padding:'10px 28px',fontSize:14,fontWeight:500,textDecoration:'none'}}>Get full report — £4.99</a>
      <p style={{fontSize:12,color:'var(--text-tertiary)',marginTop:8}}>One-time payment · Instant PDF · No subscription needed</p>
    </div>
  );
}