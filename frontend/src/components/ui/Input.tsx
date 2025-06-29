import React from 'react';
import { cn } from '../../utils/cn';
import type { InputProps } from '../../types';

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, placeholder, value, onChange, disabled, required, error, type = 'text', icon, className, ...props }, ref) => {
    return (
      <div className="space-y-2">
        {label && (
          <label className="block text-sm font-medium text-text-primary">
            {label}
            {required && <span className="text-accent ml-1">*</span>}
          </label>
        )}
        <div className="relative">
          {icon && (
            <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-text-secondary">
              {icon}
            </div>
          )}
          <input
            ref={ref}
            type={type}
            placeholder={placeholder}
            value={value}
            onChange={(e) => onChange?.(e.target.value)}
            disabled={disabled}
            required={required}
            className={cn(
              "form-input-custom",
              icon && "pl-10",
              error && "border-red-500 focus:border-red-500",
              disabled && "opacity-50 cursor-not-allowed",
              className
            )}
            {...props}
          />
        </div>
        {error && (
          <p className="text-sm text-red-500">{error}</p>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";

export { Input };