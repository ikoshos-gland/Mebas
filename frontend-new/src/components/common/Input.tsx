import { forwardRef, useState, type InputHTMLAttributes } from 'react';
import { Eye, EyeOff, AlertCircle } from 'lucide-react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      className = '',
      label,
      error,
      hint,
      leftIcon,
      rightIcon,
      type = 'text',
      id,
      ...props
    },
    ref
  ) => {
    const [showPassword, setShowPassword] = useState(false);
    const isPassword = type === 'password';
    const inputId = id || label?.toLowerCase().replace(/\s+/g, '-');

    const inputType = isPassword && showPassword ? 'text' : type;

    return (
      <div className="w-full space-y-1.5">
        {label && (
          <label
            htmlFor={inputId}
            className="font-mono-custom text-[10px] uppercase tracking-widest text-neutral-500 block"
          >
            {label}
          </label>
        )}

        <div className="relative">
          {leftIcon && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400">
              {leftIcon}
            </div>
          )}

          <input
            ref={ref}
            id={inputId}
            type={inputType}
            className={`
              w-full bg-paper border text-ink text-sm font-sans p-3 rounded-xl
              transition-all duration-200
              placeholder:text-neutral-400
              ${leftIcon ? 'pl-10' : ''}
              ${isPassword || rightIcon ? 'pr-10' : ''}
              ${error
                ? 'border-red-400 focus:border-red-500 focus:ring-1 focus:ring-red-500/20'
                : 'border-stone-200 hover:border-ink/30 focus:border-sepia focus:ring-1 focus:ring-sepia/20'
              }
              focus:outline-none
              ${className}
            `}
            {...props}
          />

          {isPassword && (
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-ink transition-colors"
            >
              {showPassword ? (
                <EyeOff className="w-4 h-4" />
              ) : (
                <Eye className="w-4 h-4" />
              )}
            </button>
          )}

          {!isPassword && rightIcon && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400">
              {rightIcon}
            </div>
          )}
        </div>

        {error && (
          <p className="flex items-center gap-1.5 text-xs text-red-600 font-sans">
            <AlertCircle className="w-3 h-3" />
            {error}
          </p>
        )}

        {hint && !error && (
          <p className="text-xs text-neutral-500 font-sans">{hint}</p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export { Input };
export type { InputProps };
