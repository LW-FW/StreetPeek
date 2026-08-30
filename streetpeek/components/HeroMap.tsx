import { useEffect, useRef } from 'react';

// Decorative street-map background for the home page hero.
const PINS: [number, number][] = [
  [0.10, 0.42], [0.20, 0.72], [0.30, 0.28], [0.42, 0.86], [0.60, 0.90],
  [0.68, 0.20], [0.80, 0.60], [0.90, 0.34], [0.94, 0.80], [0.36, 0.14],
];

const ROADS: { w: number; warm: boolean; p: [number, number][] }[] = [
  { w: 15, warm: true,  p: [[0, 0.56], [0.33, 0.48], [0.66, 0.6], [1, 0.46]] },
  { w: 15, warm: false, p: [[0.46, 0], [0.52, 0.36], [0.4, 0.68], [0.48, 1]] },
  { w: 10, warm: false, p: [[0.14, 1], [0.28, 0.64], [0.6, 0.4], [1, 0.22]] },
  { w: 10, warm: true,  p: [[0, 0.28], [0.3, 0.36], [0.7, 0.24], [1, 0.06]] },
];

export default function HeroMap({ className }: { className?: string }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;

    function draw() {
      if (!canvas) return;
      const wrap = canvas.parentElement;
      if (!wrap || wrap.offsetWidth === 0) return;
      const dpr = window.devicePixelRatio || 1;
      const W = wrap.offsetWidth, H = wrap.offsetHeight;
      canvas.width = W * dpr; canvas.height = H * dpr;
      const g = canvas.getContext('2d');
      if (!g) return;
      g.scale(dpr, dpr);

      g.fillStyle = '#F0EEE6'; g.fillRect(0, 0, W, H);

      // parks
      g.fillStyle = '#D5E7BE';
      g.beginPath(); g.ellipse(W * 0.14, H * 0.18, W * 0.13, H * 0.16, 0.3, 0, 7); g.fill();
      g.beginPath(); g.ellipse(W * 0.87, H * 0.85, W * 0.11, H * 0.14, -0.2, 0, 7); g.fill();
      // river
      g.strokeStyle = '#B3D2EE'; g.lineWidth = 9; g.lineCap = 'round';
      g.beginPath(); g.moveTo(W * 0.06, H * 0.02);
      g.bezierCurveTo(W * 0.2, H * 0.34, W * 0.16, H * 0.6, W * 0.3, H * 1.02); g.stroke();

      // minor street grid, slightly rotated: casing pass then fill pass
      for (const pass of [0, 1]) {
        g.save(); g.translate(W / 2, H / 2); g.rotate(-0.09);
        const L = Math.max(W, H) * 1.5, step = 74;
        g.strokeStyle = pass === 0 ? '#DDD9CC' : '#FBFAF6';
        g.lineWidth = pass === 0 ? 7 : 5; g.lineCap = 'butt';
        for (let x = -L / 2; x <= L / 2; x += step) { g.beginPath(); g.moveTo(x, -L / 2); g.lineTo(x, L / 2); g.stroke(); }
        for (let y = -L / 2; y <= L / 2; y += step * 1.25) { g.beginPath(); g.moveTo(-L / 2, y); g.lineTo(L / 2, y); g.stroke(); }
        g.restore();
      }

      // main roads: casing then fill
      for (const pass of [0, 1]) {
        for (const r of ROADS) {
          const [[x0, y0], [x1, y1], [x2, y2], [x3, y3]] = r.p;
          g.lineCap = 'round';
          g.strokeStyle = pass === 0 ? (r.warm ? '#E7D3A4' : '#D3CFC1') : (r.warm ? '#FCEFD2' : '#FFFFFF');
          g.lineWidth = pass === 0 ? r.w + 3 : r.w;
          g.beginPath(); g.moveTo(x0 * W, y0 * H);
          g.bezierCurveTo(x1 * W, y1 * H, x2 * W, y2 * H, x3 * W, y3 * H); g.stroke();
        }
      }

      // teardrop pins
      for (const [x, y] of PINS) {
        const px = x * W, py = y * H;
        g.fillStyle = 'rgba(26,24,18,.14)';
        g.beginPath(); g.ellipse(px, py + 2, 6, 2.4, 0, 0, 7); g.fill();
        g.fillStyle = '#F26419';
        g.beginPath();
        g.arc(px, py - 14, 8.5, Math.PI * 0.85, Math.PI * 0.15);
        g.quadraticCurveTo(px + 6, py - 6, px, py);
        g.quadraticCurveTo(px - 6, py - 6, px - 8.4, py - 16.6);
        g.closePath(); g.fill();
        g.fillStyle = '#fff';
        g.beginPath(); g.arc(px, py - 14, 3.4, 0, 7); g.fill();
      }
    }

    draw();
    window.addEventListener('resize', draw);
    return () => window.removeEventListener('resize', draw);
  }, []);

  return <canvas ref={ref} className={className} aria-hidden="true" />;
}
