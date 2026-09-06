import type { Metadata } from "next";
import "./globals.css";
import { ClerkAuthWrapper } from "@/components/ClerkAuthWrapper";

export const metadata: Metadata = {
  title: "PricePilot AI - Dynamic Pricing Optimization & Revenue Intelligence System",
  description: "AI-powered dynamic pricing platform featuring LightGBM, XGBoost, Prophet ML models, and OpenRouter Multi-Agent System.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="bg-slate-50 text-slate-900 font-sans antialiased">
        <ClerkAuthWrapper>
          {children}
        </ClerkAuthWrapper>
      </body>
    </html>
  );
}
