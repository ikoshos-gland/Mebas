import { useEffect, useState, createContext, useContext, useCallback, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from 'lucide-react';

// Toast Types
type ToastType = 'success' | 'error' | 'warning' | 'info';

interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
}

interface ToastContextValue {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
}

// Context
const ToastContext = createContext<ToastContextValue | undefined>(undefined);

// Provider Component
export const ToastProvider = ({ children }: { children: ReactNode }) => {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((toast: Omit<Toast, 'id'>) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { ...toast, id }]);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <ToastContainer />
    </ToastContext.Provider>
  );
};

// Hook
export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }

  const { addToast } = context;

  return {
    success: (title: string, message?: string) =>
      addToast({ type: 'success', title, message }),
    error: (title: string, message?: string) =>
      addToast({ type: 'error', title, message }),
    warning: (title: string, message?: string) =>
      addToast({ type: 'warning', title, message }),
    info: (title: string, message?: string) =>
      addToast({ type: 'info', title, message }),
  };
};

// Toast Container
const ToastContainer = () => {
  const context = useContext(ToastContext);
  if (!context) return null;

  const { toasts } = context;

  if (toasts.length === 0) return null;

  return createPortal(
    <div className="fixed bottom-6 right-6 z-[100] space-y-3 max-w-sm">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} />
      ))}
    </div>,
    document.body
  );
};

// Individual Toast
const ToastItem = ({ toast }: { toast: Toast }) => {
  const context = useContext(ToastContext);
  const [isExiting, setIsExiting] = useState(false);

  const typeConfig = {
    success: {
      icon: CheckCircle,
      bg: 'bg-green-50 border-green-200',
      iconColor: 'text-green-500',
      titleColor: 'text-green-800',
    },
    error: {
      icon: AlertCircle,
      bg: 'bg-red-50 border-red-200',
      iconColor: 'text-red-500',
      titleColor: 'text-red-800',
    },
    warning: {
      icon: AlertTriangle,
      bg: 'bg-amber-50 border-amber-200',
      iconColor: 'text-amber-500',
      titleColor: 'text-amber-800',
    },
    info: {
      icon: Info,
      bg: 'bg-blue-50 border-blue-200',
      iconColor: 'text-blue-500',
      titleColor: 'text-blue-800',
    },
  };

  const config = typeConfig[toast.type];
  const Icon = config.icon;

  const handleClose = useCallback(() => {
    setIsExiting(true);
    setTimeout(() => {
      context?.removeToast(toast.id);
    }, 200);
  }, [context, toast.id]);

  // Auto dismiss
  useEffect(() => {
    const duration = toast.duration ?? 5000;
    const timer = setTimeout(handleClose, duration);
    return () => clearTimeout(timer);
  }, [toast.duration, handleClose]);

  return (
    <div
      className={`
        flex items-start gap-3 p-4 rounded-xl border shadow-lg
        ${config.bg}
        ${isExiting ? 'animate-slide-out' : 'animate-enter'}
        transition-all duration-200
      `}
      role="alert"
    >
      <Icon className={`w-5 h-5 ${config.iconColor} flex-shrink-0 mt-0.5`} />

      <div className="flex-1 min-w-0">
        <p className={`font-sans font-medium text-sm ${config.titleColor}`}>
          {toast.title}
        </p>
        {toast.message && (
          <p className="text-xs text-neutral-600 mt-1">{toast.message}</p>
        )}
      </div>

      <button
        onClick={handleClose}
        className="p-1 hover:bg-white/50 rounded transition-colors flex-shrink-0"
        aria-label="Kapat"
      >
        <X className="w-4 h-4 text-neutral-500" />
      </button>
    </div>
  );
};

export { ToastContainer };
