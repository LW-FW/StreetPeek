import Head from 'next/head';
import Navbar from '../components/Navbar';
import PostcodeSearch from '../components/PostcodeSearch';
import { IconBuilding, IconWaves, IconMap, IconShield, IconTrend, IconHouse } from '../components/icons';
import styles from '../styles/Home.module.css';
import Image from 'next/image';

export default function Home() {
  return (
    <>
      <Head><title>StreetPeek — See what's coming to your street</title></Head>
      <div className={styles.page}>
        <Navbar />
        <section className={styles.hero}>
          <Image src="/logo1.png" alt="StreetPeek" width={680} height={380} priority />
          <p className={styles.subhead}>Planning applications, new developments, crime trends and more — all in one place, before you buy.</p>
          <div className={styles.searchWrap}><PostcodeSearch large /></div>
          <div className={styles.pills}>
            {['Planning applications','Housing developments','Crime statistics','Flood risk','Conservation areas','Brownfield sites','Interactive map'].map(label => (
              <span key={label} className={styles.pill}>{label}</span>
            ))}
          </div>
        </section>

        <section className={styles.features}>
          <div className={styles.featureCard}>
            <div className={styles.featureIcon} style={{background:'var(--orange-light)'}}><IconBuilding size={20} color="var(--orange)" /></div>
            <h3>Planning data</h3>
            <p>Every approved and pending development within 1 mile of any postcode, mapped and explained in plain English.</p>
          </div>
          <div className={styles.featureCard}>
            <div className={styles.featureIcon} style={{background:'var(--blue-light)'}}><IconWaves size={20} color="var(--blue)" /></div>
            <h3>Flood &amp; environment</h3>
            <p>Flood risk zones, conservation areas, green belt and tree preservation orders — all constraints that affect development.</p>
          </div>
          <div className={styles.featureCard}>
            <div className={styles.featureIcon} style={{background:'var(--orange-light)'}}><IconTrend size={20} color="var(--orange)" /></div>
            <h3>Crime trends</h3>
            <p>12-month crime data by category, compared to the national average with a clear trend direction.</p>
          </div>
          <div className={styles.featureCard}>
            <div className={styles.featureIcon} style={{background:'var(--green-light)'}}><IconHouse size={20} color="var(--green)" /></div>
            <h3>Brownfield sites</h3>
            <p>Former industrial land approved for housing — see exactly how many homes are planned and when.</p>
          </div>
          <div className={styles.featureCard}>
            <div className={styles.featureIcon} style={{background:'var(--gray-light)'}}><IconShield size={20} color="var(--gray)" /></div>
            <h3>Area protections</h3>
            <p>Conservation areas, listed buildings and green belt — factors that restrict development and protect character.</p>
          </div>
          <div className={styles.featureCard}>
            <div className={styles.featureIcon} style={{background:'var(--orange-light)'}}><IconMap size={20} color="var(--orange)" /></div>
            <h3>Interactive map</h3>
            <p>Every data point on a live map. Free view: 0.3 miles. Full report: 2-mile radius with all layers togglable.</p>
          </div>
        </section>

        <div className={styles.mapTeaser}>
          <div className={styles.mapTeaserLabel}><span className={styles.mapTeaserDot} />Interactive map on every search</div>
          <div className={styles.mapTeaserVisual}>
            <div className={styles.mapTeaserGrid} />
            <div className={styles.mapTeaserContent}>
              <div className={styles.mapPin}><div className={styles.mapPinInner} /></div>
              <div className={styles.mapRipple} /><div className={styles.mapRipple2} />
              <div className={styles.mapTeaserChip} style={{top:'-36px',left:'32px'}}><IconBuilding size={12} color="var(--orange)" />&nbsp;480 homes · 0.1mi</div>
              <div className={styles.mapTeaserChip} style={{top:'28px',left:'-120px'}}><IconWaves size={12} color="var(--blue)" />&nbsp;Flood zone · 0.4mi</div>
            </div>
            <p className={styles.mapTeaserHint}>Free: 0.3mi view &nbsp;·&nbsp; Full report: 2mi radius with all layers</p>
          </div>
        </div>

        <footer className={styles.trustBar}>
          {['planning.data.gov.uk','data.police.uk','Environment Agency','Updated weekly','Open Government Licence'].map(item => (
            <div key={item} className={styles.trustItem}><span className={styles.trustDot} />{item}</div>
          ))}
        </footer>
      </div>
    </>
  );
}