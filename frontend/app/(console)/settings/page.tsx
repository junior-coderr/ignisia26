import { Card } from "@/components/ui/card";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <Card className="p-8">
        <div className="metric-label mb-2">Settings</div>
        <h1 className="text-4xl font-semibold tracking-tight">Evaluation system configuration</h1>
        <p className="mt-4 max-w-3xl text-base leading-7 text-muted-foreground">
          This surface is ready for future controls like rubric strictness, multilingual policies, LLM review thresholds,
          and institution-level branding.
        </p>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-6">
          <div className="mb-3 text-lg font-semibold">Grading policy</div>
          <div className="text-sm leading-7 text-muted-foreground">
            The backend already supports deterministic scoring plus selective LLM review. This page can evolve into a
            control layer for administrators once authentication and tenant settings are wired in.
          </div>
        </Card>

        <Card className="p-6">
          <div className="mb-3 text-lg font-semibold">Branding and exports</div>
          <div className="text-sm leading-7 text-muted-foreground">
            The design system in this rewrite is intentionally reusable, so custom tenant theming and export templates can
            be layered in without redesigning the entire product.
          </div>
        </Card>
      </div>
    </div>
  );
}
