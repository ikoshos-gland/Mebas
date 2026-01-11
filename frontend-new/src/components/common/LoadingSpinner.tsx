import { Loader2 } from 'lucide-react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  text?: string;
}

const sizeStyles = {
  sm: 'w-4 h-4',
  md: 'w-6 h-6',
  lg: 'w-8 h-8',
};

export const LoadingSpinner = ({
  size = 'md',
  className = '',
  text,
}: LoadingSpinnerProps) => {
  return (
    <div className={`flex items-center justify-center gap-2 ${className}`}>
      <Loader2 className={`${sizeStyles[size]} animate-spin text-sepia`} />
      {text && (
        <span className="font-mono-custom text-xs text-neutral-500 uppercase tracking-wider">
          {text}
        </span>
      )}
    </div>
  );
};

// Full Page Loading
export const FullPageLoading = ({ text = 'Yükleniyor...' }: { text?: string }) => {
  return (
    <div className="fixed inset-0 bg-canvas flex items-center justify-center z-50">
      <div className="text-center animate-enter">
        <div className="w-16 h-16 mb-4 mx-auto relative">
          <div className="absolute inset-0 border-2 border-stone-200 rounded-full" />
          <div className="absolute inset-0 border-2 border-sepia border-t-transparent rounded-full animate-spin" />
        </div>
        <p className="font-mono-custom text-xs text-neutral-500 uppercase tracking-widest">
          {text}
        </p>
      </div>
    </div>
  );
};

// Skeleton Components
export const Skeleton = ({ className = '' }: { className?: string }) => (
  <div className={`bg-stone-200 rounded animate-pulse ${className}`} />
);

export const SkeletonText = ({ lines = 3 }: { lines?: number }) => (
  <div className="space-y-2">
    {Array.from({ length: lines }).map((_, i) => (
      <Skeleton
        key={i}
        className={`h-3 ${i === lines - 1 ? 'w-2/3' : 'w-full'}`}
      />
    ))}
  </div>
);

export const SkeletonCard = () => (
  <div className="card-surface p-6 rounded-2xl space-y-4">
    <div className="flex items-center gap-3">
      <Skeleton className="w-10 h-10 rounded-full" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="h-3 w-1/4" />
      </div>
    </div>
    <SkeletonText lines={3} />
  </div>
);
