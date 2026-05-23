import { ButtonHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

const styles: Record<Variant, string> = {
  primary:
    "bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm disabled:bg-gray-700 disabled:cursor-not-allowed",
  secondary:
    "bg-gray-700 hover:bg-gray-600 text-white",
  ghost:
    "bg-transparent hover:bg-gray-800 text-gray-300 border border-gray-700",
};

export const Button = forwardRef<HTMLButtonElement, Props>(
  ({ variant = "primary", className, ...rest }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center gap-2 px-4 py-2 rounded-md font-medium text-sm transition-colors",
        styles[variant],
        className
      )}
      {...rest}
    />
  )
);
Button.displayName = "Button";
