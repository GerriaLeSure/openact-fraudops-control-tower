import React from "react";

export function KpiCards({ kpis }: { kpis: { label: string; value: string }[] }) {
  return (
    <div className="grid md:grid-cols-3 gap-4">
      {kpis.map((k, i) => (
        <div key={i} className="rounded-2xl shadow p-4">
          <div className="text-sm text-gray-500">{k.label}</div>
          <div className="text-2xl font-semibold">{k.value}</div>
        </div>
      ))}
    </div>
  );
}
