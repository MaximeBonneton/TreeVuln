import { Info, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';

interface AlertProps {
  variant?: 'info' | 'success' | 'warning' | 'error';
  title?: string;
  children: React.ReactNode;
}

const variants = {
  info: { classes: 'border-indigo-200 bg-indigo-50 text-indigo-800', Icon: Info },
  success: { classes: 'border-emerald-200 bg-emerald-50 text-emerald-800', Icon: CheckCircle2 },
  warning: { classes: 'border-amber-200 bg-amber-50 text-amber-800', Icon: AlertTriangle },
  error: { classes: 'border-red-200 bg-red-50 text-red-800', Icon: XCircle },
};

export function Alert({ variant = 'info', title, children }: AlertProps) {
  const { classes, Icon } = variants[variant];
  return (
    <div role="alert" className={`flex gap-3 rounded-lg border px-4 py-3 text-sm ${classes}`}>
      <Icon size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
      <div>
        {title && <p className="font-semibold">{title}</p>}
        <div>{children}</div>
      </div>
    </div>
  );
}
