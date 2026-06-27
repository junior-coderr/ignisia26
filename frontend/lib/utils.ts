import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatGradeBand(band?: string | null) {
  if (!band) return "Ungraded";
  if (typeof band !== "string") return "Mixed";
  if (band === "formula_half_credit") return "Formula correct, arithmetic wrong";
  if (band === "excellent") return "Excellent";
  if (band === "good") return "Good";
  if (band === "average") return "Average";
  if (band === "poor") return "Needs Improvement";
  return band
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function scoreTone(scoreRatio: number) {
  if (scoreRatio >= 0.8) return "text-emerald-500";
  if (scoreRatio >= 0.45) return "text-amber-500";
  return "text-rose-500";
}

export function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function initials(value: string) {
  return value
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

export function highlightByTerms(text: string, terms: string[]) {
  if (!text || !terms.length) return [{ text, active: false }];
  const escaped = terms
    .filter((term) => term.trim().length >= 2)
    .map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  if (!escaped.length) return [{ text, active: false }];
  const regex = new RegExp(`(${escaped.join("|")})`, "gi");
  const exactTerms = escaped.map((term) => new RegExp(`^${term}$`, "i"));
  return text.split(regex).filter(Boolean).map((part) => ({
    text: part,
    active: exactTerms.some((pattern) => pattern.test(part)),
  }));
}
