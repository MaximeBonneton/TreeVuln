import { useState, useCallback } from 'react';

interface ConfirmState {
  open: boolean;
  title: string;
  message: string;
  variant: 'danger' | 'warning' | 'info';
  resolve: ((value: boolean) => void) | null;
}

interface ConfirmOptions {
  title: string;
  message: string;
  confirmLabel?: string;
  danger?: boolean;
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
    (titleOrOptions: string | ConfirmOptions, message?: string, variant: 'danger' | 'warning' | 'info' = 'danger'): Promise<boolean> => {
      let title: string;
      let resolvedMessage: string;
      let resolvedVariant: 'danger' | 'warning' | 'info' = variant;

      if (typeof titleOrOptions === 'string') {
        // Legacy 3-param API: confirm(title, message, variant?)
        title = titleOrOptions;
        resolvedMessage = message || '';
        resolvedVariant = variant;
      } else {
        // Object API: confirm({ title, message, confirmLabel?, danger? })
        title = titleOrOptions.title;
        resolvedMessage = titleOrOptions.message;
        resolvedVariant = titleOrOptions.danger ? 'danger' : 'warning';
      }

      return new Promise<boolean>((resolve) => {
        setState({ open: true, title, message: resolvedMessage, variant: resolvedVariant, resolve });
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
