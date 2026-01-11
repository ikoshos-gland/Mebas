import { useEffect, useCallback, type ReactNode } from 'react';
import { X } from 'lucide-react';
import { createPortal } from 'react-dom';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  showCloseButton?: boolean;
  closeOnOverlayClick?: boolean;
  closeOnEsc?: boolean;
}

const sizeStyles = {
  sm: 'max-w-md',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl',
  full: 'max-w-[90vw] max-h-[90vh]',
};

const Modal = ({
  isOpen,
  onClose,
  title,
  children,
  size = 'md',
  showCloseButton = true,
  closeOnOverlayClick = true,
  closeOnEsc = true,
}: ModalProps) => {
  // Handle ESC key
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (closeOnEsc && e.key === 'Escape') {
        onClose();
      }
    },
    [closeOnEsc, onClose]
  );

  // Lock body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      document.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      document.body.style.overflow = 'unset';
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, handleKeyDown]);

  if (!isOpen) return null;

  const modalContent = (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? 'modal-title' : undefined}
    >
      {/* Overlay */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-enter"
        onClick={closeOnOverlayClick ? onClose : undefined}
        aria-hidden="true"
      />

      {/* Modal Content */}
      <div
        className={`
          relative w-full ${sizeStyles[size]}
          bg-paper rounded-2xl shadow-2xl
          animate-enter overflow-hidden
          flex flex-col
        `}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        {(title || showCloseButton) && (
          <div className="flex items-center justify-between p-6 border-b border-stone-200">
            {title && (
              <h2
                id="modal-title"
                className="font-serif-custom text-xl italic text-ink"
              >
                {title}
              </h2>
            )}
            {showCloseButton && (
              <button
                onClick={onClose}
                className="p-2 hover:bg-stone-100 rounded-full transition-colors ml-auto"
                aria-label="Kapat"
              >
                <X className="w-5 h-5 text-neutral-500" />
              </button>
            )}
          </div>
        )}

        {/* Body */}
        <div className="p-6 overflow-auto flex-1">{children}</div>
      </div>
    </div>
  );

  // Use portal to render modal at document root
  return createPortal(modalContent, document.body);
};

// Confirm Dialog variant
interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'danger' | 'warning' | 'default';
  isLoading?: boolean;
}

const ConfirmDialog = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = 'Onayla',
  cancelText = 'Iptal',
  variant = 'default',
  isLoading = false,
}: ConfirmDialogProps) => {
  const confirmButtonStyles = {
    default: 'bg-ink text-paper hover:bg-sepia',
    warning: 'bg-amber-500 text-white hover:bg-amber-600',
    danger: 'bg-red-600 text-white hover:bg-red-700',
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} size="sm">
      <p className="text-neutral-600 font-sans mb-6">{message}</p>

      <div className="flex justify-end gap-3">
        <button
          onClick={onClose}
          disabled={isLoading}
          className="px-4 py-2 text-neutral-600 hover:text-ink hover:bg-stone-100 rounded-lg transition-colors font-mono-custom text-xs uppercase tracking-wider"
        >
          {cancelText}
        </button>
        <button
          onClick={onConfirm}
          disabled={isLoading}
          className={`
            px-4 py-2 rounded-lg font-mono-custom text-xs uppercase tracking-wider
            transition-all active:scale-95 disabled:opacity-50
            ${confirmButtonStyles[variant]}
          `}
        >
          {isLoading ? 'Yukleniyor...' : confirmText}
        </button>
      </div>
    </Modal>
  );
};

export { Modal, ConfirmDialog };
export type { ModalProps, ConfirmDialogProps };
