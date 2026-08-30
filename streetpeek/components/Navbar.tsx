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
      <span />
      <Link href="/" className={`${styles.logo} ${montserrat.className}`}>
        Street<span className={styles.divider}>|</span><span className={styles.peek}>Peek</span>
      </Link>

      <button className={styles.signIn}>Sign in</button>
    </nav>
  );
}