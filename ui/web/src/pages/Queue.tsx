import React, { useEffect, useState } from "react";
import { API } from "../api/client";

export default function Queue() {
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    API.listCases().then(setRows).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-6">Loading…</div>;

  return (
    <div className="p-6">
      <h1 className="text-xl font-semibold mb-4">Open Cases</h1>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left border-b">
            <th>Case ID</th><th>Entity</th><th>Risk</th><th>Action</th><th>Status</th><th>Assignee</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r._id} className="border-b hover:bg-gray-50">
              <td><a className="text-blue-600" href={`/case/${r._id}`}>{r._id}</a></td>
              <td>{r.entity_id}</td>
              <td>{(r.risk*100).toFixed(1)}%</td>
              <td>{r.action}</td>
              <td>{r.status}</td>
              <td>{r.assignee ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
