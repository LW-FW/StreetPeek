import Head from 'next/head';
import { useEffect, useState } from 'react';
import Navbar from '../components/Navbar';
import Badge from '../components/Badge';
import { IconAlert } from '../components/icons';
import styles from '../styles/DataSources.module.css';

const SECTIONS = [
  { id: 'overview', label: 'Overview' },
  { id: 'location-crime', label: 'Location & crime' },
  { id: 'planning-environment', label: 'Planning & environment' },
  { id: 'amenities', label: 'Amenities' },
  { id: 'schools-nurseries', label: 'Schools & nurseries' },
  { id: 'score-method', label: 'Area score method' },
  { id: 'limitations', label: 'Known limitations' },
];

export default function DataSources() {
  const [active, setActive] = useState('overview');

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter(e => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActive(visible[0].target.id);
      },
      { rootMargin: '-100px 0px -70% 0px' }
    );
    SECTIONS.forEach(s => {
      const el = document.getElementById(s.id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, []);

  return (
    <>
      <Head><title>Data & methodology — StreetPeek</title></Head>
      <div className={styles.page}>
        <Navbar />

        <div className={styles.hero}>
          <h1 className={styles.headline}>Data &amp; methodology</h1>
          <p className={styles.sub}>A reference sheet for every source behind a StreetPeek report — what it covers, how fresh it is, and where it falls short. If a number on your report looks off, this is where to check it against the original.</p>
        </div>

        <div className={styles.disclaimerWrap}>
          <div className={styles.disclaimer}>
            <span className={styles.disclaimerIcon}><IconAlert size={19} /></span>
            <p><b>StreetPeek is a research tool, not professional advice.</b> It doesn&apos;t replace a solicitor&apos;s local searches, a RICS survey, or independent legal advice before you buy — use it to know what to ask a professional, not instead of one.</p>
          </div>
        </div>

        <div className={styles.layout}>
          <div className={styles.side}>
            <div className={styles.sideTitle}>On this page</div>
            {SECTIONS.map(s => (
              <a key={s.id} href={`#${s.id}`} className={`${styles.sideLink} ${active === s.id ? styles.sideLinkActive : ''}`}>{s.label}</a>
            ))}
          </div>

          <div>
            <div className={styles.section} id="overview">
              <h2>Why we publish this</h2>
              <p className={styles.sectionIntro}>Every layer of a report links back to a public source, on purpose — so you can double-check anything on your report, learn how to vet a home yourself, and use StreetPeek because it&apos;s convenient rather than because it&apos;s the only way to see this. We&apos;d rather you verify us than just trust us.</p>
            </div>

            <div className={styles.section} id="location-crime">
              <h2>Location &amp; crime</h2>
              <p className={styles.sectionIntro}>The foundation of every report: where the postcode sits, and what&apos;s been reported nearby.</p>
              <div className={styles.cardGrid}>
                <div className={styles.srcCard}>
                  <div className={styles.srcCardHead}><span className={styles.srcCardName}>Postcode lookup</span><Badge variant="good">Live</Badge></div>
                  <p>Postcode → map point, ward, district, constituency.</p>
                  <a href="https://postcodes.io" target="_blank" rel="noopener noreferrer">postcodes.io (ONS data) ↗</a>
                </div>
                <div className={styles.srcCard}>
                  <div className={styles.srcCardHead}><span className={styles.srcCardName}>Crime</span><Badge variant="good">Live</Badge></div>
                  <p>Street-level crime counts by category, latest published month. Locations are anonymised to a nearby point.</p>
                  <a href="https://data.police.uk" target="_blank" rel="noopener noreferrer">data.police.uk ↗</a>
                </div>
              </div>
            </div>

            <div className={styles.section} id="planning-environment">
              <h2>Planning &amp; environment</h2>
              <p className={styles.sectionIntro}>National planning data, aggregated from what individual councils publish — so coverage is only as good as each council&apos;s own open-data feed.</p>
              <div className={styles.cardGrid}>
                <div className={styles.srcCard}>
                  <div className={styles.srcCardHead}><span className={styles.srcCardName}>Planning applications</span><Badge variant="warn">Varies by council</Badge></div>
                  <p>Nearby applications, brownfield sites, infrastructure projects.</p>
                  <a href="https://www.planning.data.gov.uk" target="_blank" rel="noopener noreferrer">planning.data.gov.uk ↗</a>
                </div>
                <div className={styles.srcCard}>
                  <div className={styles.srcCardHead}><span className={styles.srcCardName}>Environment &amp; heritage</span><Badge variant="warn">Varies by council</Badge></div>
                  <p>Flood zones, conservation areas, green belt, listed buildings, TPOs, ancient woodland.</p>
                  <a href="https://www.planning.data.gov.uk" target="_blank" rel="noopener noreferrer">planning.data.gov.uk ↗</a>
                </div>
                <div className={`${styles.srcCard} ${styles.fullWidth}`}>
                  <div className={styles.srcCardHead}><span className={styles.srcCardName}>In progress: direct council portal data</span><Badge variant="neutral">Not all live yet</Badge></div>
                  <p>We&apos;re building direct connections into individual council planning portals to fill the gaps national data misses. Not all 300+ councils we&apos;re mapping are wired in today — a blank result can mean &quot;nothing found&quot; or &quot;not connected yet,&quot; and we&apos;re working to close that gap.</p>
                </div>
              </div>
            </div>

            <div className={styles.section} id="amenities">
              <h2>Amenities</h2>
              <p className={styles.sectionIntro}>Community-maintained map data — strong UK coverage overall, but quality depends on local volunteer mapping.</p>
              <div className={styles.cardGrid}>
                <div className={`${styles.srcCard} ${styles.fullWidth}`}>
                  <div className={styles.srcCardHead}><span className={styles.srcCardName}>GPs, dentists, pharmacies, supermarkets, gyms</span><Badge variant="info">Community-mapped</Badge></div>
                  <p>Sourced from OpenStreetMap via the Overpass API. Can be patchy or out of date on a specific street even where the wider area is well mapped.</p>
                  <a href="https://www.openstreetmap.org" target="_blank" rel="noopener noreferrer">openstreetmap.org ↗</a>
                </div>
              </div>
            </div>

            <div className={styles.section} id="schools-nurseries">
              <h2>Schools &amp; nurseries</h2>
              <p className={styles.sectionIntro}>Official DfE and Ofsted registers, refreshed monthly to match Ofsted&apos;s own publishing cycle.</p>
              <div className={styles.cardGrid}>
                <div className={`${styles.srcCard} ${styles.fullWidth}`}>
                  <div className={styles.srcCardHead}><span className={styles.srcCardName}>GIAS + Ofsted + ONS NSPL</span><Badge variant="good">Refreshed monthly</Badge></div>
                  <p>School/nursery register, latest Ofsted rating, and postcode-to-location matching.</p>
                  <ul className={styles.miniList}>
                    <li>Ofsted&apos;s published figures can lag the actual inspection by a few weeks</li>
                    <li>Independent schools appear in the register but aren&apos;t Ofsted-rated (they&apos;re inspected by the ISI instead)</li>
                    <li>Schools are mid-transition to Ofsted&apos;s new rating system — most still carry a rating under the old one, and we label which applies</li>
                  </ul>
                </div>
              </div>
            </div>

            <div className={styles.section} id="score-method">
              <h2>Area score method</h2>
              <p className={styles.sectionIntro}>A single number meant as a rough compass, not a verdict — built transparently from the sources above.</p>
              <table className={styles.scoreTable}>
                <thead><tr><th>Signal</th><th>Adjustment</th></tr></thead>
                <tbody>
                  <tr><td>Baseline</td><td>7.0</td></tr>
                  <tr><td>Crime over 200/month</td><td>−2</td></tr>
                  <tr><td>Crime over 100/month</td><td>−1</td></tr>
                  <tr><td>Crime under 30/month</td><td>+1</td></tr>
                  <tr><td>Flood risk zone nearby</td><td>−1</td></tr>
                  <tr><td>Conservation area nearby</td><td>+0.5</td></tr>
                  <tr><td>Brownfield housing site nearby</td><td>+0.5</td></tr>
                  <tr><td>Final score, capped</td><td>1–10</td></tr>
                </tbody>
              </table>
            </div>

            <div className={styles.section} id="limitations">
              <h2>Known limitations</h2>
              <ul className={styles.miniList} style={{fontSize:13.5}}>
                <li>Council-published planning &amp; environment data is uneven — silence isn&apos;t proof of &quot;clear&quot;</li>
                <li>Crime figures are roughly a month or more behind today, and locations are approximate by design</li>
                <li>Amenity data quality depends on volunteer mapping in that specific area</li>
                <li>The area score reflects only crime, flood, conservation and brownfield signals — not schools, transport, or amenities yet</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
