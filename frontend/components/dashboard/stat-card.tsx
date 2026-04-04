"use client";

import { motion } from "framer-motion";
import { ArrowUpRight } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

export function StatCard({
  label,
  value,
  detail,
  icon,
}: {
  label: string;
  value: string;
  detail: string;
  icon: React.ReactNode;
}) {
  return (
    <motion.div whileHover={{ y: -4 }} transition={{ duration: 0.22 }}>
      <Card className="overflow-hidden">
        <CardContent className="relative p-6">
          <div className="absolute right-0 top-0 h-24 w-24 rounded-full bg-primary/10 blur-2xl" />
          <div className="mb-6 flex items-center justify-between">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              {icon}
            </div>
            <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
          </div>
          <div className="metric-label mb-2">{label}</div>
          <div className="text-3xl font-semibold tracking-tight">{value}</div>
          <p className="mt-2 text-sm text-muted-foreground">{detail}</p>
        </CardContent>
      </Card>
    </motion.div>
  );
}
