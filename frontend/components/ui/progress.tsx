import { cn } from "@/lib/utils";

export function Progress({
  value,
  className,
  indeterminate = false,
}: {
  value: number;
  className?: string;
  indeterminate?: boolean;
}) {
  const clamped = Math.max(0, Math.min(100, value));

  return (
    <div className={cn("relative h-2 w-full overflow-hidden rounded-full bg-muted/60", className)}>
      <div
        className={cn(
          "h-full rounded-full bg-gradient-to-r from-primary via-primary/85 to-accent",
          indeterminate
            ? "w-1/3 animate-[indeterminate_1.5s_ease-in-out_infinite]"
            : "transition-[width] duration-700 ease-out",
        )}
        style={indeterminate ? undefined : { width: `${clamped}%` }}
      />
      {/* Shimmer overlay */}
      {(clamped > 0 || indeterminate) && (
        <div
          className="absolute inset-0 animate-shimmer rounded-full"
          style={{
            background:
              "linear-gradient(90deg, transparent, rgba(255,255,255,0.2) 50%, transparent)",
            backgroundSize: "200% 100%",
          }}
        />
      )}
    </div>
  );
}
