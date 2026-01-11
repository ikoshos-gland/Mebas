import { forwardRef, type HTMLAttributes } from 'react';

type CardVariant = 'surface' | 'glass' | 'outlined' | 'elevated';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant;
  padding?: 'none' | 'sm' | 'md' | 'lg';
  hover?: boolean;
}

const variantStyles: Record<CardVariant, string> = {
  surface: 'card-surface',
  glass: 'glass-vellum',
  outlined: 'bg-transparent border border-stone-200',
  elevated: 'card-surface shadow-lg',
};

const paddingStyles = {
  none: '',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
};

const Card = forwardRef<HTMLDivElement, CardProps>(
  (
    {
      className = '',
      variant = 'surface',
      padding = 'md',
      hover = false,
      children,
      ...props
    },
    ref
  ) => {
    return (
      <div
        ref={ref}
        className={`
          rounded-2xl
          ${variantStyles[variant]}
          ${paddingStyles[padding]}
          ${hover ? 'transition-all duration-200 hover:shadow-md hover:-translate-y-0.5' : ''}
          ${className}
        `}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';

// Card Header subcomponent
interface CardHeaderProps extends HTMLAttributes<HTMLDivElement> {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}

const CardHeader = forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ className = '', title, subtitle, action, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={`flex items-start justify-between mb-4 pb-4 border-b border-stone-200 ${className}`}
        {...props}
      >
        <div>
          <h3 className="font-serif-custom text-lg italic text-sepia">{title}</h3>
          {subtitle && (
            <p className="font-mono-custom text-[10px] text-neutral-500 mt-1 uppercase tracking-widest">
              {subtitle}
            </p>
          )}
        </div>
        {action && <div>{action}</div>}
      </div>
    );
  }
);

CardHeader.displayName = 'CardHeader';

// Card Content subcomponent
interface CardContentProps extends HTMLAttributes<HTMLDivElement> {}

const CardContent = forwardRef<HTMLDivElement, CardContentProps>(
  ({ className = '', children, ...props }, ref) => {
    return (
      <div ref={ref} className={`prose-meba ${className}`} {...props}>
        {children}
      </div>
    );
  }
);

CardContent.displayName = 'CardContent';

// Card Footer subcomponent
interface CardFooterProps extends HTMLAttributes<HTMLDivElement> {}

const CardFooter = forwardRef<HTMLDivElement, CardFooterProps>(
  ({ className = '', children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={`flex items-center gap-3 mt-4 pt-4 border-t border-stone-200/60 ${className}`}
        {...props}
      >
        {children}
      </div>
    );
  }
);

CardFooter.displayName = 'CardFooter';

export { Card, CardHeader, CardContent, CardFooter };
export type { CardProps, CardHeaderProps, CardContentProps, CardFooterProps };
