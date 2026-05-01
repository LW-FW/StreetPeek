import Head from 'next/head';
import Navbar from '../components/Navbar';
import styles from '../styles/Pricing.module.css';

const plans = [
  { name:'Free', price:'£0', desc:'Get a feel for any area instantly.', features:['Basic crime headline','1 brownfield site result','0.3mi map view','Area summary'], cta:'Start searching', href:'/', highlight:false },
  { name:'Full report', price:'£4.99', desc:'One-time payment. Everything for one postcode.', features:['All planning applications','Full brownfield + infrastructure data','2mi interactive map','12-month crime breakdown','Flood & environment detail','PDF to share with solicitor'], cta:'Buy report', href:'/', highlight:true },
  { name:'Pro', price:'£9.99/mo', desc:'For active buyers and investors.', features:['Unlimited postcode searches','Email alerts for new applications','All full report features','Save and compare areas'], cta:'Coming soon', href:'#', highlight:false },
];

export default function Pricing() {
  return (
    <>
      <Head><title>Pricing — StreetPeek</title></Head>
      <div className={styles.page}>
        <Navbar />
        <div className={styles.hero}>
          <h1 className={styles.headline}>Simple, transparent pricing</h1>
          <p className={styles.sub}>Start free. Pay only when you need the full picture.</p>
        </div>
        <div className={styles.grid}>
          {plans.map(plan=>(
            <div key={plan.name} className={`${styles.card} ${plan.highlight?styles.highlight:''}`}>
              {plan.highlight&&<div className={styles.badge}>Most popular</div>}
              <div className={styles.planName}>{plan.name}</div>
              <div className={styles.price}>{plan.price}</div>
              <p className={styles.desc}>{plan.desc}</p>
              <ul className={styles.features}>
                {plan.features.map(f=>(
                  <li key={f}>
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6.5" stroke={plan.highlight?'var(--orange)':'var(--green)'} strokeWidth="1.3"/><path d="M5.5 8.5L7 10L10.5 6.5" stroke={plan.highlight?'var(--orange)':'var(--green)'} strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/></svg>
                    {f}
                  </li>
                ))}
              </ul>
              <a href={plan.href} className={`${styles.cta} ${plan.highlight?styles.ctaHighlight:''}`}>{plan.cta}</a>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}