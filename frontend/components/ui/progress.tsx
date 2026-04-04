import { cn } from "@/lib/utils";

export function Progress({
  value,
  className,
}: {
  value: number;
  className?: string;
}) {
  return (
    <div className={cn("relative h-2.5 w-full overflow-hidden rounded-full bg-muted/80", className)}>
      <div
        className="h-full rounded-full bg-[linear-gradient(90deg,#2563eb,#22d3ee)] transition-all duration-500"
        style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
      />
    </div>
  );
}
