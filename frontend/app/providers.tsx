"use client";

import { ThemeProvider } from "next-themes";
import { Toaster } from "sonner";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem disableTransitionOnChange>
      {children}
      <Toaster
        richColors
        position="bottom-right"
        toastOptions={{
          className: "rounded-xl border border-border/50 bg-card/95 text-foreground backdrop-blur-xl text-sm",
          duration: 3500,
        }}
      />
    </ThemeProvider>
  );
}
