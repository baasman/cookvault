import React from 'react';
import { cn } from '../../utils/cn';
import type { TextareaProps } from '../../types';

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, placeholder, value, onChange, disabled, required, error, rows = 4, className, ...props }, ref) => {
    return (
      <div className="space-y-2">
        {label && (
          <label className="block text-sm font-medium text-text-primary">
            {label}
            {required && <span className="text-accent ml-1">*</span>}
          </label>
        )}
        <textarea
          ref={ref}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange?.(e.target.value)}
          disabled={disabled}
          required={required}
          rows={rows}
          className={cn(
            "form-input-custom resize-none",
            error && "border-red-500 focus:border-red-500",
            disabled && "opacity-50 cursor-not-allowed",
            className
          )}
          {...props}
        />
        {error && (
          <p className="text-sm text-red-500">{error}</p>
        )}
      </div>
    );
  }
);

Textarea.displayName = "Textarea";

export { Textarea };