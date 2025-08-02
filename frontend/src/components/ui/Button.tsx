import React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../utils/cn';

const buttonVariants = cva(
  // Base styles - extracted from template analysis
  "inline-flex items-center justify-center font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 disabled:pointer-events-none disabled:opacity-50 cursor-pointer",
  {
    variants: {
      variant: {
        // Primary button - orange CTA from templates
        primary: "text-white hover:opacity-90 rounded-full tracking-[0.015em]",
        // Secondary button - light background from templates  
        secondary: "rounded-full tracking-[0.015em]",
        // Outline button - border variant
        outline: "border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 rounded-full tracking-[0.015em]",
        // Pill variant - for filter buttons from templates
        pill: "rounded-full",
      },
      size: {
        sm: "h-8 px-4 text-sm",
        md: "h-10 px-4 text-sm font-bold leading-normal",
        lg: "h-14 px-6 text-base font-bold leading-normal",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  }
);

interface ExtendedButtonProps 
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  children: React.ReactNode;
}

const Button = React.forwardRef<HTMLButtonElement, ExtendedButtonProps>(
  ({ className, variant, size, children, style, ...props }, ref) => {
    const getButtonStyle = () => {
      if (variant === 'primary') {
        return { backgroundColor: '#f15f1c', color: '#ffffff', ...style };
      }
      if (variant === 'secondary') {
        return { backgroundColor: '#f1ece9', color: '#1c120d', ...style };
      }
      return style;
    };

    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        style={getButtonStyle()}
        ref={ref}
        {...props}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";

export { Button, buttonVariants };