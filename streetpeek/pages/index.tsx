import Head from 'next/head';
import Image from 'next/image';
import Navbar from '../components/Navbar';
import PostcodeSearch from '../components/PostcodeSearch';
import HeroMap from '../components/HeroMap';
import { IconBuilding, IconWaves, IconMap, IconShield, IconTrend, IconHouse } from '../components/icons';
import styles from '../styles/Home.module.css';

const LAYERS = [
  { color: 'var(--orange)', name: 'Planning applications', note: "from the council's own portal" },
  { color: 'var(--orange-dark)', name: 'New developments', note: 'homes planned & how far along' },
  { color: 'var(--amber)', name: 'Crime trends', note: '12 months, street level' },
  { color: 'var(--blue)', name: 'Flood risk', note: 'Environment Agency zones' },
  { color: 'var(--green)', name: 'Schools & Ofsted', note: 'every school within a mile' },
  { color: 'var(--gray)', name: 'Protections', note: 'conservation, green belt, listed' },
  { color: 'var(--text-primary)', name: 'The verdict', note: 'a plain-English area score' },
];

export default function Home() {
  return (
    <>
      <Head><title>StreetPeek — Peek into the future of your street</title></Head>
      <div className={styles.page}>
        <Navbar />

        <header className={styles.hero}>
          <HeroMap className={styles.heroMap} />
          <div className={styles.heroVeil} />

          <div className={styles.chip} style={{top:'24%',left:'9%'}} aria-hidden="true"><span className={styles.chipDot} style={{background:'var(--orange)'}}/><b>54 homes</b>· pending · 0.3 mi</div>
          <div className={styles.chip} style={{top:'38%',right:'7%',animationDelay:'-2s'}} aria-hidden="true"><span className={styles.chipDot} style={{background:'var(--blue)'}}/><b>No flood zone</b>· within 0.8 mi</div>
          <div className={styles.chip} style={{bottom:'22%',left:'7%',animationDelay:'-4s'}} aria-hidden="true"><span className={styles.chipDot} style={{background:'var(--green)'}}/><b>Ofsted Outstanding</b>· 0.6 mi</div>
          <div className={styles.chip} style={{bottom:'14%',right:'10%',animationDelay:'-5.5s'}} aria-hidden="true"><span className={styles.chipDot} style={{background:'var(--amber)'}}/><b>Conservation area</b>· adjacent</div>

          <div className={styles.heroCard}>
            <Image src="/Logo.png" alt="StreetPeek" width={400} height={218} priority className={styles.heroLogo} />
            <h1 className={styles.headline}>Peek into the future of <em>your street</em>.</h1>
            <p className={styles.subhead}>One postcode. Every planning application, development, crime figure and school — read straight from official records.</p>
            <div className={styles.searchWrap}><PostcodeSearch large /></div>
            <p className={styles.heroNote}>Free area preview · Full report £4.99 · No account needed</p>
          </div>
        </header>

        <section className={styles.layers}>
          <span className={styles.sectionEyebrow}>What you get</span>
          <h2 className={styles.sectionTitle}>One search. Seven layers.</h2>
          <p className={styles.sectionSub}>Each layer togglable on the map, all of them in the report.</p>
          <div className={styles.layerGrid}>
            {LAYERS.map(l => (
              <div key={l.name} className={styles.layer}>
                <span className={styles.layerDot} style={{background:l.color}} />
                <b>{l.name}</b><span>{l.note}</span>
              </div>
            ))}
          </div>
        </section>

        <section className={styles.features}>
          <div className={styles.featureGrid}>
            <div className={styles.featureCard}>
              <span className={styles.featureGlow} style={{background:'var(--orange-light)'}} />
              <div className={styles.featureIcon} style={{background:'linear-gradient(135deg,var(--orange-light),#fff)'}}><IconBuilding size={20} color="var(--orange)" /></div>
              <h3>Planning data</h3>
              <p>Every approved and pending development within 1 mile of any postcode, mapped and explained in plain English.</p>
            </div>
            <div className={styles.featureCard}>
              <span className={styles.featureGlow} style={{background:'var(--blue-light)'}} />
              <div className={styles.featureIcon} style={{background:'linear-gradient(135deg,var(--blue-light),#fff)'}}><IconWaves size={20} color="var(--blue)" /></div>
              <h3>Flood &amp; environment</h3>
              <p>Flood risk zones, conservation areas, green belt and tree preservation orders — all constraints that affect development.</p>
            </div>
            <div className={styles.featureCard}>
              <span className={styles.featureGlow} style={{background:'var(--amber-light)'}} />
              <div className={styles.featureIcon} style={{background:'linear-gradient(135deg,var(--amber-light),#fff)'}}><IconTrend size={20} color="var(--amber)" /></div>
              <h3>Crime trends</h3>
              <p>12-month crime data by category, compared to the national average with a clear trend direction.</p>
            </div>
            <div className={styles.featureCard}>
              <span className={styles.featureGlow} style={{background:'var(--green-light)'}} />
              <div className={styles.featureIcon} style={{background:'linear-gradient(135deg,var(--green-light),#fff)'}}><IconHouse size={20} color="var(--green)" /></div>
              <h3>Brownfield sites</h3>
              <p>Former industrial land approved for housing — see exactly how many homes are planned and when.</p>
            </div>
            <div className={styles.featureCard}>
              <span className={styles.featureGlow} style={{background:'var(--gray-light)'}} />
              <div className={styles.featureIcon} style={{background:'linear-gradient(135deg,var(--gray-light),#fff)'}}><IconShield size={20} color="var(--gray)" /></div>
              <h3>Area protections</h3>
              <p>Conservation areas, listed buildings and green belt — factors that restrict development and protect character.</p>
            </div>
            <div className={styles.featureCard}>
              <span className={styles.featureGlow} style={{background:'var(--orange-light)'}} />
              <div className={styles.featureIcon} style={{background:'linear-gradient(135deg,var(--orange-light),#fff)'}}><IconMap size={20} color="var(--orange)" /></div>
              <h3>Interactive map</h3>
              <p>Every data point on a live map. Free view: 0.3 miles. Full report: 2-mile radius with all layers togglable.</p>
            </div>
          </div>
        </section>

        <section className={styles.sources}>
          <span className={styles.sectionEyebrow}>Our data</span>
          <h2 className={styles.sectionTitle}>Built on official records</h2>
          <p className={styles.sectionSub}>Nothing scraped from forums or guesswork — every layer comes from the source.</p>
          <div className={styles.sourceRow}>
            <span className={styles.sourcePill}><b>Council planning portals</b>&nbsp;· 275 councils</span>
            <span className={styles.sourcePill}><b>data.police.uk</b>&nbsp;· street-level crime</span>
            <span className={styles.sourcePill}><b>Environment Agency</b>&nbsp;· flood zones</span>
            <span className={styles.sourcePill}><b>planning.data.gov.uk</b>&nbsp;· designations</span>
            <span className={styles.sourcePill}><b>GIAS</b>&nbsp;· schools register</span>
          </div>
          <p className={styles.sourceFoot}>Refreshed weekly · Published under the Open Government Licence</p>
        </section>

        <footer className={styles.footer}>© 2026 StreetPeek · Peek into the future of your area</footer>
      </div>
    </>
  );
}
