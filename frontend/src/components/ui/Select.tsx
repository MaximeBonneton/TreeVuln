import { forwardRef } from 'react';
import { fieldClasses, invalidFieldClasses } from './fieldStyles';

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  invalid?: boolean;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { invalid = false, className = '', children, ...props },
  ref
) {
  return (
    <select
      ref={ref}
      aria-invalid={invalid || undefined}
      className={`${fieldClasses} ${invalid ? invalidFieldClasses : ''} ${className}`}
      {...props}
    >
      {children}
    </select>
  );
});
