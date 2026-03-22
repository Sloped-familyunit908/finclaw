import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/app/lib/cn";

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-gray-800 text-gray-200",
        secondary:
          "border-transparent bg-gray-800/60 text-gray-400",
        destructive:
          "border-transparent bg-red-950/60 text-red-300",
        outline: "text-gray-300 border-gray-700/50",
        success:
          "border-transparent bg-emerald-950/60 text-emerald-300",
        warning:
          "border-transparent bg-yellow-950/60 text-yellow-300",
        info:
          "border-transparent bg-blue-950/60 text-blue-300",
        purple:
          "border-transparent bg-purple-950/60 text-purple-300",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
