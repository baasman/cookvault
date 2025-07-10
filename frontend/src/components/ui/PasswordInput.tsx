import React, { useState } from 'react';
import { Input } from './Input';
import type { InputProps } from '../../types';

interface PasswordInputProps extends Omit<InputProps, 'type' | 'icon'> {
  showToggle?: boolean;
}

const PasswordInput = React.forwardRef<HTMLInputElement, PasswordInputProps>(
  ({ showToggle = true, className, ...props }, ref) => {
    const [showPassword, setShowPassword] = useState(false);

    const togglePasswordVisibility = () => {
      setShowPassword(!showPassword);
    };

    const toggleIcon = showToggle ? (
      <button
        type="button"
        onClick={togglePasswordVisibility}
        className="absolute right-3 top-1/2 transform -translate-y-1/2 text-text-secondary hover:text-text-primary transition-colors focus:outline-none"
        aria-label={showPassword ? 'Hide password' : 'Show password'}
      >
        {showPassword ? (
          // Eye slash icon (hide password)
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={2} 
              d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L8.464 8.464m1.414 1.414L14.12 14.12m0 0l1.415 1.415M14.12 14.12A10.025 10.025 0 0012 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029M6.757 6.757L3 3m18 18l-3.757-3.757M6.757 6.757l7.07 7.07" 
            />
          </svg>
        ) : (
          // Eye icon (show password)
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={2} 
              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" 
            />
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={2} 
              d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" 
            />
          </svg>
        )}
      </button>
    ) : null;

    return (
      <div className="relative">
        <Input
          ref={ref}
          type={showPassword ? 'text' : 'password'}
          className={`${showToggle ? 'pr-12' : ''} ${className || ''}`}
          {...props}
        />
        {toggleIcon}
      </div>
    );
  }
);

PasswordInput.displayName = "PasswordInput";

export { PasswordInput };