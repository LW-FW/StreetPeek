import Link from 'next/link';
import { Montserrat } from 'next/font/google';
import styles from './Navbar.module.css';

const montserrat = Montserrat({
  subsets: ['latin'],
  weight: ['700'],
});

export default function Navbar() {
  return (
    <nav className={styles.nav}>
      <Link href="/" className={`${styles.logo} ${montserrat.className}`}>
        Street<span className={styles.divider}>|</span><span className={styles.peek}>Peek</span>
      </Link>
      
      <div className={styles.links}>
        <Link href="/how-it-works">How it works</Link>
        <Link href="/pricing">Pricing</Link>
        <Link href="/sample">Sample report</Link>
      </div>
      
      <button className={styles.signIn}>Sign in</button>
    </nav>
  );
}