"use client";

import AIApprovalDashboard from "../AIApprovalDashboard";
import ClipManagement from "../ClipManagement";

export default function CommandCenter() {
  return (
    <>
      <div className="mb-8">
        <AIApprovalDashboard />
      </div>
      <div className="mb-8">
        <ClipManagement />
      </div>
    </>
  );
}
