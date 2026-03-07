import * as React from "react";
import { cn } from "@/lib/utils";

interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: number;
  max?: number;
  indicatorClassName?: string;
}

const Progress = React.forwardRef<HTMLDivElement, ProgressProps>(
  ({ className, value = 0, max = 100, indicatorClassName, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("relative h-3 w-full overflow-hidden rounded-full bg-secondary", className)}
      {...props}
    >
      <div
        className={cn("h-full rounded-full bg-primary transition-all duration-500", indicatorClassName)}
        style={{ width: `${Math.min(100, (value / max) * 100)}%` }}
      />
    </div>
  )
);
Progress.displayName = "Progress";

export { Progress };
