import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { QueryProvider } from "@/providers/query-provider";
import { AuthProvider } from "@/providers/auth-provider";
import { NotificationProvider } from "@/providers/notification-provider";
import { Toaster } from "sonner";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "RestoOps — AI-Powered Restaurant Operations",
  description: "Automated Lead Intake, Email Verification, Multi-Channel Engagement, WebRTC Calling & AI Human-in-the-Loop Operations Dashboard.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-[#090d16] text-slate-100 antialiased selection:bg-indigo-500 selection:text-white`}>
        <QueryProvider>
          <AuthProvider>
            <NotificationProvider>
              {children}
              <Toaster theme="dark" position="top-right" richColors />
            </NotificationProvider>
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
