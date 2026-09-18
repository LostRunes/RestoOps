import React from "react";
import LeadDetailClient from "./client";

export async function generateStaticParams() {
  return [{ id: "new" }];
}

export default function LeadDetailPage({ params }: { params: Promise<{ id: string }> }) {
  return <LeadDetailClient params={params} />;
}
