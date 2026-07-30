import { forwardRef } from 'react';
import { fieldClasses, invalidFieldClasses } from './fieldStyles';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { invalid = false, className = '', ...props },
  ref
) {
  return (
    <input
      ref={ref}
      aria-invalid={invalid || undefined}
      className={`${fieldClasses} ${invalid ? invalidFieldClasses : ''} ${className}`}
      {...props}
    />
  );
});
