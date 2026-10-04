export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 100 100" className={className} fill="currentColor" aria-hidden="true">
      <path d="M62,18 L82,18 L58,46 L58,86 L42,86 L42,54 L46,46 Z" />
      <path d="M18,18 L38,18 L46,30 L30,30 Z" />
    </svg>
  );
}

export function Logo({ subtitle }: { subtitle?: string }) {
  return (
    <div className="flex items-center gap-3">
      <LogoMark className="h-8 w-8 text-[#f0a500]" />
      <div>
        <div className="text-sm font-bold uppercase tracking-wider text-white">Lynsus</div>
        {subtitle && <div className="text-[11px] text-white/40">{subtitle}</div>}
      </div>
    </div>
  );
}
