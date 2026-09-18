import React from "react";
import CampaignBuilderClient from "./client";

export async function generateStaticParams() {
  return [{ id: "new" }];
}

export default function CampaignBuilderPage({ params }: { params: Promise<{ id: string }> }) {
  return <CampaignBuilderClient params={params} />;
}
