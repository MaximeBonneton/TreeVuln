import { Dialog } from './Dialog';
import { Button } from './Button';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
  variant?: 'danger' | 'warning' | 'info';
}

// Style du bouton de confirmation selon la gravité de l'action
const confirmButtonVariant: Record<
  NonNullable<ConfirmDialogProps['variant']>,
  'danger' | 'warning' | 'primary'
> = {
  danger: 'danger',
  warning: 'warning',
  info: 'primary',
};

export function ConfirmDialog({
  open,
  title,
  message,
  onConfirm,
  onCancel,
  variant = 'danger',
}: ConfirmDialogProps) {
  return (
    <Dialog
      open={open}
      onClose={onCancel}
      title={title}
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
          <Button variant={confirmButtonVariant[variant]} onClick={onConfirm}>
            Confirm
          </Button>
        </>
      }
    >
      <p className="text-sm text-slate-600">{message}</p>
    </Dialog>
  );
}
