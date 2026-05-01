import styles from './Badge.module.css';
type BadgeVariant = 'good' | 'warn' | 'info' | 'orange' | 'neutral' | 'red';
interface BadgeProps { variant?: BadgeVariant; children: React.ReactNode; }
export default function Badge({ variant = 'neutral', children }: BadgeProps) {
  return <span className={`${styles.badge} ${styles[variant]}`}>{children}</span>;
}