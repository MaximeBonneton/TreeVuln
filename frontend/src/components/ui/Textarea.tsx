import { forwardRef } from 'react';
import { fieldClasses, invalidFieldClasses } from './fieldStyles';

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalid?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { invalid = false, className = '', ...props },
  ref
) {
  return (
    <textarea
      ref={ref}
      aria-invalid={invalid || undefined}
      className={`${fieldClasses} ${invalid ? invalidFieldClasses : ''} font-mono ${className}`}
      {...props}
    />
  );
});
