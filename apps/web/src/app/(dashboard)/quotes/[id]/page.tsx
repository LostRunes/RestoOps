import React from "react";
import QuoteEditorClient from "./client";

export async function generateStaticParams() {
  return [{ id: "new" }];
}

export default function QuoteEditorPage({ params }: { params: Promise<{ id: string }> }) {
  return <QuoteEditorClient params={params} />;
}
