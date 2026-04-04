"use client";

import { ThemeProvider } from "next-themes";
import { Toaster } from "sonner";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem disableTransitionOnChange>
      {children}
      <Toaster
        richColors
        position="top-right"
        toastOptions={{
          className: "rounded-2xl border border-border/70 bg-card/90 text-foreground backdrop-blur-xl",
        }}
      />
    </ThemeProvider>
  );
}
