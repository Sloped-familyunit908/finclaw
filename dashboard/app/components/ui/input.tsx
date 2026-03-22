import * as React from "react";
import { cn } from "@/app/lib/cn";

const Input = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className, type, ...props }, ref) => {
  return (
    <input
      type={type}
      className={cn(
        "flex h-9 w-full rounded-md border border-gray-700/50 bg-gray-900/60 px-3 py-1.5 text-xs text-gray-300 shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-gray-300 placeholder:text-gray-600 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-slate-500/60 disabled:cursor-not-allowed disabled:opacity-50 font-mono",
        className,
      )}
      ref={ref}
      {...props}
    />
  );
});
Input.displayName = "Input";

export { Input };
