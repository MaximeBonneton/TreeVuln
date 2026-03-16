import { Lock } from 'lucide-react';

interface EnterpriseBadgeProps {
  feature: string;
  className?: string;
}

export function EnterpriseBadge({ feature, className }: EnterpriseBadgeProps) {
  return (
    <button
      disabled
      className={`flex items-center gap-1.5 opacity-50 cursor-not-allowed text-gray-400 ${className ?? ''}`}
      title={`${feature} — disponible en version Enterprise`}
    >
      <Lock size={14} />
      <span className="text-sm">{feature}</span>
      <span className="text-[10px] bg-gray-200 text-gray-500 px-1.5 py-0.5 rounded font-medium">
        Enterprise
      </span>
    </button>
  );
}
