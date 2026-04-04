import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium tracking-wide",
  {
    variants: {
      variant: {
        neutral: "border-border/70 bg-muted/70 text-muted-foreground",
        success: "border-emerald-500/25 bg-emerald-500/10 text-emerald-500",
        warning: "border-amber-500/25 bg-amber-500/10 text-amber-500",
        danger: "border-rose-500/25 bg-rose-500/10 text-rose-500",
        info: "border-primary/25 bg-primary/10 text-primary",
      },
    },
    defaultVariants: {
      variant: "neutral",
    },
  },
);

export function Badge({
  className,
  variant,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & VariantProps<typeof badgeVariants>) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}
