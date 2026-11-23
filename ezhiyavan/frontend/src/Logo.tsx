// Brand mark and a warm welcome illustration (inline SVG: no image downloads, works offline, decorative only).
export function Logo({ size = 40 }: { size?: number }) {
  return (<svg className="logo" width={size} height={size} viewBox="0 0 48 48" aria-hidden="true">
    <rect width="48" height="48" rx="12" fill="#1f6b3a" />
    <path d="M24 37V22" stroke="#fbf6e9" strokeWidth="3" strokeLinecap="round" />
    <path d="M24 26c-7 0-10-4-10-9 7 0 10 4 10 9zM24 22c0-5 3-9 10-9 0 5-3 9-10 9z" fill="#f2c94c" />
    <path d="M10 39h28" stroke="#fbf6e9" strokeWidth="3" strokeLinecap="round" />
  </svg>);
}

export function Illustration() {
  return (<svg className="illus" viewBox="0 0 320 150" aria-hidden="true">
    <rect width="320" height="150" rx="18" fill="#fff3cd" />
    <circle cx="262" cy="36" r="20" fill="#f2c94c" />
    <path d="M0 108Q60 78 120 98T240 92T320 98V150H0z" fill="#8fc79d" />
    <path d="M0 126Q80 100 160 118T320 114V150H0z" fill="#1f6b3a" />
    {[24, 52, 80, 108, 136].map(x => <g key={x}><path d={`M${x} 142v-14`} stroke="#fbf6e9" strokeWidth="2" strokeLinecap="round" /><path d={`M${x} 134q-8 0-9-8 8 0 9 8zM${x} 131q8 0 9-8-8 0-9 8z`} fill="#f2c94c" /></g>)}
    <rect x="196" y="52" width="56" height="88" rx="10" fill="#fff" stroke="#1f6b3a" strokeWidth="3" />
    <rect x="218" y="68" width="12" height="20" rx="6" fill="#1f6b3a" />
    <path d="M212 84a12 12 0 0 0 24 0M224 96v8" stroke="#1f6b3a" strokeWidth="3" fill="none" strokeLinecap="round" />
    <path d="M184 86a14 14 0 0 1 0 20M174 80a26 26 0 0 1 0 32" stroke="#1f6b3a" strokeWidth="3" fill="none" strokeLinecap="round" />
  </svg>);
}
