import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Synovo : AI Conversational Intelligence",
  description:
    "Synovo: AI-powered conversation analysis — transcription, diarization, behavioral analytics, semantic search, and contradiction detection.",
  icons: {
    icon: [{ url: "/Brain.svg", type: "image/svg+xml", sizes: "any" }],
    shortcut: "/Brain.svg",
    apple: "/Brain.svg",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body>{children}</body>
    </html>
  );
}
