import { useState } from 'react';
import { useRouter } from 'next/router';
import { IconSearch } from './icons';
import styles from './PostcodeSearch.module.css';

interface PostcodeSearchProps { large?: boolean; defaultValue?: string; }

export default function PostcodeSearch({ large = false, defaultValue = '' }: PostcodeSearchProps) {
  const [value, setValue] = useState(defaultValue);
  const [error, setError] = useState('');
  const router = useRouter();

  const isValidPostcode = (pc: string) => /^[A-Z]{1,2}\d[A-Z\d]?\d[A-Z]{2}$/.test(pc.replace(/\s/g,'').toUpperCase());

  const handleSearch = () => {
    const clean = value.trim().toUpperCase();
    if (!clean) { setError('Please enter a postcode'); return; }
    if (!isValidPostcode(clean)) { setError('Please enter a valid UK postcode'); return; }
    setError('');
    router.push(`/results?postcode=${encodeURIComponent(clean)}`);
  };

  return (
    <div className={styles.wrap}>
      <div className={`${styles.box} ${large ? styles.large : ''} ${error ? styles.hasError : ''}`}>
        <span className={styles.icon}><IconSearch size={16} color="var(--text-tertiary)"/></span>
        <input
          type="text" placeholder="Enter a postcode, e.g. E1 6RF"
          value={value} onChange={e => { setValue(e.target.value); setError(''); }}
          onKeyDown={e => e.key === 'Enter' && handleSearch()}
          maxLength={8} autoComplete="postal-code" aria-label="Enter a UK postcode"
        />
        <button onClick={handleSearch}>Check area</button>
      </div>
      {error && <p className={styles.error}>{error}</p>}
      <p className={styles.hint}>
        Try:{' '}
        {['E1 6RF ','M1 1AE ','BS1 4DJ '].map(pc => (
          <span key={pc} onClick={() => { setValue(pc); setError(''); }} className={styles.example}>{pc}</span>
        ))}
      </p>
    </div>
  );
}