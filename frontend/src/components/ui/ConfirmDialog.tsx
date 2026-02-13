interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
  variant?: 'danger' | 'warning' | 'info';
}

const variantStyles = {
  danger: {
    button: 'bg-red-500 hover:bg-red-600 text-white',
    icon: 'text-red-500',
  },
  warning: {
    button: 'bg-orange-500 hover:bg-orange-600 text-white',
    icon: 'text-orange-500',
  },
  info: {
    button: 'bg-blue-500 hover:bg-blue-600 text-white',
    icon: 'text-blue-500',
  },
};

export function ConfirmDialog({
  open,
  title,
  message,
  onConfirm,
  onCancel,
  variant = 'danger',
}: ConfirmDialogProps) {
  if (!open) return null;

  const styles = variantStyles[variant];

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-96 max-w-[90vw]">
        <h3 className="text-lg font-bold text-gray-800 mb-2">{title}</h3>
        <p className="text-sm text-gray-600 mb-6">{message}</p>
        <div className="flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-md text-sm"
          >
            Annuler
          </button>
          <button
            onClick={onConfirm}
            className={`px-4 py-2 rounded-md text-sm font-medium ${styles.button}`}
          >
            Confirmer
          </button>
        </div>
      </div>
    </div>
  );
}
