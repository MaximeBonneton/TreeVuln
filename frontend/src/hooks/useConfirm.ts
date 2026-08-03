import { useState, useCallback } from 'react';

interface ConfirmState {
  open: boolean;
  title: string;
  message: string;
  variant: 'danger' | 'warning' | 'info';
  resolve: ((value: boolean) => void) | null;
}

export function useConfirm() {
  const [state, setState] = useState<ConfirmState>({
    open: false,
    title: '',
    message: '',
    variant: 'danger',
    resolve: null,
  });

  const confirm = useCallback(
    (title: string, message: string, variant: 'danger' | 'warning' | 'info' = 'danger'): Promise<boolean> => {
      return new Promise<boolean>((resolve) => {
        setState({ open: true, title, message, variant, resolve });
      });
    },
    []
  );

  const handleConfirm = useCallback(() => {
    state.resolve?.(true);
    setState((s) => ({ ...s, open: false, resolve: null }));
  }, [state.resolve]);

  const handleCancel = useCallback(() => {
    state.resolve?.(false);
    setState((s) => ({ ...s, open: false, resolve: null }));
  }, [state.resolve]);

  return {
    confirm,
    confirmDialogProps: {
      open: state.open,
      title: state.title,
      message: state.message,
      variant: state.variant,
      onConfirm: handleConfirm,
      onCancel: handleCancel,
    },
  };
}
