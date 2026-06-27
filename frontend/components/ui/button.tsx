"use client";

import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap text-[17px] font-normal transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 active:scale-[0.96]",
  {
    variants: {
      variant: {
        default: "bg-[#0066cc] text-white rounded-full hover:bg-[#0071e3]",
        secondary: "bg-[#fafafc] text-[#1d1d1f] border border-[#e0e0e0] rounded-[11px] hover:bg-[#f5f5f7] text-[14px]",
        ghost: "text-[#7a7a7a] hover:bg-[#f5f5f7] hover:text-[#1d1d1f] rounded-[8px] text-[14px]",
        darkUtility: "bg-[#1d1d1f] text-white rounded-[8px] hover:bg-[#333333] text-[14px]",
      },
      size: {
        default: "px-[22px] py-[11px]",
        sm: "px-[14px] py-[8px]",
        lg: "px-[28px] py-[14px] text-[18px]",
        icon: "h-11 w-11 rounded-full",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />;
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
