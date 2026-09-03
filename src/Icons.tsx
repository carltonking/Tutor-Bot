// Minimal line icons (no emojis) — stroke follows currentColor
type P = { size?: number; className?: string };

function svgProps(size: number, className?: string) {
  return {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.6,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    className,
    style: { display: "block" as const },
  };
}

export function SearchIcon({ size = 16, className }: P) {
  return (
    <svg {...svgProps(size, className)}>
      <circle cx="11" cy="11" r="7" />
      <path d="M20 20l-3.5-3.5" />
    </svg>
  );
}

export function PlusIcon({ size = 16, className }: P) {
  return (
    <svg {...svgProps(size, className)}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

export function BotIcon({ size = 16, className }: P) {
  return (
    <svg {...svgProps(size, className)}>
      <rect x="5" y="8" width="14" height="11" rx="3" />
      <path d="M12 8V4.5M9.5 13.5h.01M14.5 13.5h.01" />
      <circle cx="12" cy="4" r="1" />
    </svg>
  );
}

export function PencilIcon({ size = 14, className }: P) {
  return (
    <svg {...svgProps(size, className)}>
      <path d="M4 20h4L19.5 8.5a2.1 2.1 0 0 0-3-3L5 17v3z" />
      <path d="M13.5 6.5l3 3" />
    </svg>
  );
}

export function DotsIcon({ size = 16, className }: P) {
  return (
    <svg {...svgProps(size, className)} fill="currentColor" stroke="none">
      <circle cx="5" cy="12" r="1.7" />
      <circle cx="12" cy="12" r="1.7" />
      <circle cx="19" cy="12" r="1.7" />
    </svg>
  );
}

export function GearIcon({ size = 16, className }: P) {
  return (
    <svg {...svgProps(size, className)}>
      <circle cx="12" cy="12" r="3.2" />
      <path d="M19 12a7 7 0 0 0-.15-1.4l2-1.55-2-3.46-2.35.95a7 7 0 0 0-2.4-1.4L13.7 2.7h-3.4l-.4 2.44a7 7 0 0 0-2.4 1.4l-2.35-.95-2 3.46 2 1.55A7 7 0 0 0 5 12c0 .47.05.94.15 1.4l-2 1.55 2 3.46 2.35-.95a7 7 0 0 0 2.4 1.4l.4 2.44h3.4l.4-2.44a7 7 0 0 0 2.4-1.4l2.35.95 2-3.46-2-1.55c.1-.46.15-.93.15-1.4z" />
    </svg>
  );
}

export function LogoutIcon({ size = 16, className }: P) {
  return (
    <svg {...svgProps(size, className)}>
      <path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3" />
      <path d="M10 17l-5-5 5-5M5 12h11" />
    </svg>
  );
}

export function AttachIcon({ size = 18, className }: P) {
  return (
    <svg {...svgProps(size, className)}>
      <path d="M21 11.5l-8.6 8.6a5.5 5.5 0 0 1-7.8-7.8l8.7-8.7a3.7 3.7 0 0 1 5.2 5.2l-8.7 8.7a1.8 1.8 0 0 1-2.6-2.6l8-8" />
    </svg>
  );
}

export function AppleIcon({ size = 18, className }: P) {
  return (
    <svg {...svgProps(size, className)} fill="currentColor" stroke="none">
      <path d="M16.7 12.9c0-2.4 2-3.6 2.1-3.7-1.1-1.7-2.9-1.9-3.5-1.9-1.5-.2-2.9.9-3.7.9-.8 0-1.9-.9-3.2-.9-1.6 0-3.1 1-4 2.4-1.7 2.9-.4 7.3 1.2 9.7.8 1.2 1.8 2.5 3 2.4 1.2 0 1.7-.8 3.2-.8s1.9.8 3.2.8c1.3 0 2.2-1.2 3-2.4.9-1.4 1.3-2.7 1.3-2.8-.1 0-2.6-1-2.6-3.7zM14.4 5.3c.7-.8 1.1-1.9 1-3-1 0-2.1.7-2.8 1.5-.6.7-1.2 1.9-1 3 1.1.1 2.2-.6 2.8-1.5z" />
    </svg>
  );
}

export function GoogleIcon({ size = 18, className }: P) {
  return (
    <svg {...svgProps(size, className)} strokeWidth={1.8}>
      <path d="M20.5 12.2c0-.6-.05-1.2-.16-1.8H12v3.5h4.8a4.1 4.1 0 0 1-1.8 2.7v2.2h2.9c1.7-1.6 2.6-3.9 2.6-6.6z" />
      <path d="M12 21c2.4 0 4.5-.8 6-2.2l-2.9-2.2c-.8.6-1.9.9-3.1.9-2.4 0-4.4-1.6-5.1-3.8H3.9v2.3A9 9 0 0 0 12 21z" />
      <path d="M6.9 13.7a5.4 5.4 0 0 1 0-3.4V8H3.9a9 9 0 0 0 0 8l3-2.3z" />
      <path d="M12 6.6c1.3 0 2.5.5 3.4 1.3l2.6-2.6A9 9 0 0 0 3.9 8l3 2.3c.7-2.2 2.7-3.7 5.1-3.7z" />
    </svg>
  );
}
