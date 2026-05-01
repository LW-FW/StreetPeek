interface IconProps { size?: number; color?: string; className?: string; }

export function IconSearch({ size=18, color='currentColor', className }: IconProps) {
  return <svg width={size} height={size} viewBox="0 0 18 18" fill="none" className={className}><circle cx="8" cy="8" r="5" stroke={color} strokeWidth="1.6"/><path d="M12 12L15.5 15.5" stroke={color} strokeWidth="1.6" strokeLinecap="round"/></svg>;
}
export function IconHouse({ size=18, color='currentColor', className }: IconProps) {
  return <svg width={size} height={size} viewBox="0 0 18 18" fill="none" className={className}><path d="M2 16H16M3 16V8.5L9 3L15 8.5V16M7 16V11H11V16" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>;
}
export function IconBuilding({ size=18, color='currentColor', className }: IconProps) {
  return <svg width={size} height={size} viewBox="0 0 18 18" fill="none" className={className}><rect x="2" y="11" width="4" height="6" rx="0.5" fill={color}/><rect x="7" y="7" width="4" height="10" rx="0.5" fill={color} opacity="0.65"/><rect x="12" y="4" width="4" height="13" rx="0.5" fill={color} opacity="0.35"/></svg>;
}
export function IconWaves({ size=18, color='currentColor', className }: IconProps) {
  return <svg width={size} height={size} viewBox="0 0 18 18" fill="none" className={className}><path d="M2 12C4 12 4 9.5 7 9.5C10 9.5 10 12 13 12C16 12 16 9.5 18 9.5" stroke={color} strokeWidth="1.5" strokeLinecap="round"/><path d="M2 8.5C4 8.5 4 6.5 7 6.5C10 6.5 10 8.5 13 8.5C16 8.5 16 6.5 18 6.5" stroke={color} strokeWidth="1.5" strokeLinecap="round" opacity="0.45"/></svg>;
}
export function IconShield({ size=18, color='currentColor', className }: IconProps) {
  return <svg width={size} height={size} viewBox="0 0 18 18" fill="none" className={className}><path d="M9 2L15 5V10C15 13.5 12 16 9 17C6 16 3 13.5 3 10V5L9 2Z" stroke={color} strokeWidth="1.5" strokeLinejoin="round"/></svg>;
}
export function IconTrend({ size=18, color='currentColor', className }: IconProps) {
  return <svg width={size} height={size} viewBox="0 0 18 18" fill="none" className={className}><path d="M2 14L6 9L9.5 11.5L14 5.5L17 7.5" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>;
}
export function IconMapPin({ size=18, color='currentColor', className }: IconProps) {
  return <svg width={size} height={size} viewBox="0 0 18 18" fill="none" className={className}><circle cx="9" cy="7.5" r="3.5" stroke={color} strokeWidth="1.5"/><path d="M9 11v5M6.5 15.5h5" stroke={color} strokeWidth="1.5" strokeLinecap="round"/></svg>;
}
export function IconMap({ size=18, color='currentColor', className }: IconProps) {
  return <svg width={size} height={size} viewBox="0 0 18 18" fill="none" className={className}><path d="M1 4L6 2L12 5L17 3V15L12 17L6 14L1 16V4Z" stroke={color} strokeWidth="1.5" strokeLinejoin="round"/><path d="M6 2V14M12 5V17" stroke={color} strokeWidth="1.5"/></svg>;
}
export function IconAlert({ size=18, color='currentColor', className }: IconProps) {
  return <svg width={size} height={size} viewBox="0 0 18 18" fill="none" className={className}><path d="M9 2L16.5 15.5H1.5L9 2Z" stroke={color} strokeWidth="1.5" strokeLinejoin="round"/><path d="M9 7.5v3.5" stroke={color} strokeWidth="1.5" strokeLinecap="round"/><circle cx="9" cy="13" r="0.8" fill={color}/></svg>;
}
export function IconTick({ size=18, color='currentColor', className }: IconProps) {
  return <svg width={size} height={size} viewBox="0 0 18 18" fill="none" className={className}><circle cx="9" cy="9" r="7.5" stroke={color} strokeWidth="1.4"/><path d="M5.5 9.5L7.5 11.5L12.5 6.5" stroke={color} strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/></svg>;
}
export function IconCross({ size=18, color='currentColor', className }: IconProps) {
  return <svg width={size} height={size} viewBox="0 0 18 18" fill="none" className={className}><circle cx="9" cy="9" r="7.5" stroke={color} strokeWidth="1.4"/><path d="M6 9h6" stroke={color} strokeWidth="1.4" strokeLinecap="round"/></svg>;
}
export function IconCrime({ size=18, color='currentColor', className }: IconProps) {
  return <svg width={size} height={size} viewBox="0 0 18 18" fill="none" className={className}><path d="M9 2L11.5 7H16.5L12.5 10.5L14 16L9 12.5L4 16L5.5 10.5L1.5 7H6.5L9 2Z" stroke={color} strokeWidth="1.4" strokeLinejoin="round"/></svg>;
}
export function IconCalendar({ size=18, color='currentColor', className }: IconProps) {
  return <svg width={size} height={size} viewBox="0 0 18 18" fill="none" className={className}><rect x="2" y="3.5" width="14" height="13" rx="1.5" stroke={color} strokeWidth="1.4"/><path d="M2 7.5h14M6 2v3M12 2v3" stroke={color} strokeWidth="1.4" strokeLinecap="round"/></svg>;
}
export function IconDocument({ size=18, color='currentColor', className }: IconProps) {
  return <svg width={size} height={size} viewBox="0 0 18 18" fill="none" className={className}><path d="M4 2h7l4 4v11a1 1 0 01-1 1H4a1 1 0 01-1-1V3a1 1 0 011-1z" stroke={color} strokeWidth="1.4" strokeLinejoin="round"/><path d="M11 2v4h4M6 9h6M6 12h4" stroke={color} strokeWidth="1.4" strokeLinecap="round"/></svg>;
}