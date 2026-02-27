import React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../utils/cn';
import { isIOS, isNativePlatform } from '../../utils/platform';
import { lightImpact } from '../../utils/haptics';

const buttonVariants = cva(
  // Base styles - extracted from template analysis
  "inline-flex items-center justify-center font-medium transition-all focus-visible:outline-none focus-visible:ring-2 disabled:pointer-events-none disabled:opacity-50 cursor-pointer",
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
        sm: "h-10 px-6 text-sm gap-2",
        md: "h-12 px-8 text-sm font-bold leading-normal gap-2",
        lg: "h-14 px-10 text-base font-bold leading-normal gap-3",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  }
);

// Check if we're on native iOS for touch states
const isNativeIOS = (): boolean => isIOS() && isNativePlatform();

interface ExtendedButtonProps 
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  children: React.ReactNode;
}

const Button = React.forwardRef<HTMLButtonElement, ExtendedButtonProps>(
  ({ className, variant, size, children, style, onClick, ...props }, ref) => {
    // Default variant to 'primary' if not specified (matches defaultVariants in cva)
    const effectiveVariant = variant ?? 'primary';

    const getButtonStyle = () => {
      if (effectiveVariant === 'primary') {
        return { backgroundColor: '#f15f1c', color: '#ffffff', ...style };
      }
      if (effectiveVariant === 'secondary') {
        return { backgroundColor: '#f1ece9', color: '#1c120d', ...style };
      }
      return style;
    };

    // iOS-specific touch class for press feedback
    const iosTouchClass = isNativeIOS() ? 'active:scale-[0.97] active:opacity-90' : '';

    const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
      // Trigger haptic feedback on native iOS
      if (isNativeIOS()) {
        lightImpact();
      }
      onClick?.(e);
    };

    return (
      <button
        className={cn(buttonVariants({ variant, size }), iosTouchClass, className)}
        style={getButtonStyle()}
        ref={ref}
        onClick={handleClick}
        {...props}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";

export { Button, buttonVariants };