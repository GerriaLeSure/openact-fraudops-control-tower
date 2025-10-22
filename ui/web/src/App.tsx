import React from "react";
const Queue = React.lazy(()=>import("./pages/Queue"));
const CaseView = React.lazy(()=>import("./pages/CaseView"));
const Analytics = React.lazy(()=>import("./pages/Analytics"));

export default function App() {
  const path = window.location.pathname;
  
  if (path.startsWith("/case/")) {
    return (
      <React.Suspense fallback={<div className="p-6">Loading…</div>}>
        <CaseView/>
      </React.Suspense>
    );
  }
  
  if (path === "/analytics") {
    return (
      <React.Suspense fallback={<div className="p-6">Loading…</div>}>
        <Analytics/>
      </React.Suspense>
    );
  }
  
  return (
    <React.Suspense fallback={<div className="p-6">Loading…</div>}>
      <Queue/>
    </React.Suspense>
  );
}
