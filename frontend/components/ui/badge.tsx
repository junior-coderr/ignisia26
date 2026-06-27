import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-3 py-1.5 text-[12px] font-normal tracking-[-0.12px]",
  {
    variants: {
      variant: {
        neutral: "border-[#e0e0e0] bg-[#ffffff] text-[#1d1d1f]",
        success: "border-[#00b259]/30 bg-[#00b259]/10 text-[#00b259]",
        warning: "border-[#f5a623]/30 bg-[#f5a623]/10 text-[#f5a623]",
        danger: "border-[#ff3b30]/30 bg-[#ff3b30]/10 text-[#ff3b30]",
        info: "border-[#0066cc]/30 bg-[#0066cc]/10 text-[#0066cc]",
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
