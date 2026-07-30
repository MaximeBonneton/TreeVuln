import { useState } from 'react';

interface TooltipProps {
  content: string;
  children: React.ReactNode;
}

// À état (pas CSS-only) : affichage au survol ET au focus clavier, testable en jsdom
export function Tooltip({ content, children }: TooltipProps) {
  const [visible, setVisible] = useState(false);

  return (
    <span
      className="relative inline-block"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
      onFocus={() => setVisible(true)}
      onBlur={() => setVisible(false)}
    >
      {children}
      {visible && (
        <span
          role="tooltip"
          className="absolute bottom-full left-1/2 z-50 mb-1.5 -translate-x-1/2 whitespace-nowrap rounded-md bg-slate-900 px-2 py-1 text-xs text-white shadow-md"
        >
          {content}
        </span>
      )}
    </span>
  );
}
