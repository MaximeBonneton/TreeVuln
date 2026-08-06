import { useEffect, useRef, useState } from 'react';
import { Check, Copy } from 'lucide-react';

interface CopyButtonProps {
  value: string;
  /** Nom accessible (défaut : « Copier »). */
  label?: string;
}

/** Bouton de copie presse-papier avec feedback ✓ pendant 2 s. */
export function CopyButton({ value, label = 'Copier' }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => () => clearTimeout(timeoutRef.current), []);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      clearTimeout(timeoutRef.current);
      timeoutRef.current = setTimeout(() => setCopied(false), 2000);
    } catch {
      // Presse-papier indisponible (permissions) : pas de feedback, pas de crash
    }
  };

  return (
    <button
      type="button"
      aria-label={label}
      onClick={handleCopy}
      className="rounded-md p-1 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
    >
      {copied ? (
        <Check size={14} data-testid="copy-done" className="text-emerald-600" />
      ) : (
        <Copy size={14} />
      )}
    </button>
  );
}
