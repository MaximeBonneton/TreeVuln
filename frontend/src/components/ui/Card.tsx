interface CardProps {
  title?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export function Card({ title, actions, children, className = '' }: CardProps) {
  return (
    <div className={`rounded-card border border-slate-200 bg-white shadow-sm ${className}`}>
      {(title || actions) && (
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
          {title && (
            <h3 className="text-sm font-semibold tracking-tight text-slate-900">{title}</h3>
          )}
          {actions}
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
}
