import React, { useEffect, useState } from "react";
import { API } from "../api/client";

export default function CaseView() {
  const id = window.location.pathname.split("/").pop()!;
  const [data, setData] = useState<any | null>(null);
  const [note, setNote] = useState("");

  useEffect(() => { API.getCase(id).then(setData); }, [id]);

  if (!data) return <div className="p-6">Loading…</div>;

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-semibold">Case {id}</h1>
      <div className="grid md:grid-cols-2 gap-4">
        <div className="rounded-2xl shadow p-4">
          <div className="text-gray-500 text-sm">Entity</div>
          <div className="text-lg">{data.entity_id}</div>
          <div className="mt-2 text-gray-500 text-sm">Risk</div>
          <div className="text-lg">{(data.risk*100).toFixed(1)}%</div>
          <div className="mt-2 text-gray-500 text-sm">Action</div>
          <div className="text-lg">{data.action}</div>
        </div>
        <div className="rounded-2xl shadow p-4">
          <div className="font-semibold mb-2">Add Note</div>
          <div className="flex gap-2">
            <input className="border rounded px-3 py-2 flex-1" value={note} onChange={e=>setNote(e.target.value)} placeholder="Investigator note…" />
            <button className="rounded bg-black text-white px-4" onClick={async()=>{
              await API.addNote(id, note); setNote("");
            }}>Save</button>
          </div>
        </div>
      </div>
    </div>
  );
}
