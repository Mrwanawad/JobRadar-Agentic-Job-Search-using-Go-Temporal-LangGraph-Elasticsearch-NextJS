import type { Metadata } from "next";
import Link from "next/link";
import { Geist, Geist_Mono } from "next/font/google";
import { UserMenu } from "@/components/user-menu";
import { REPO_URL } from "@/lib/site";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "JobRadar",
  description:
    "Agentic job search: Go + Temporal ingestion, LangGraph agents and hybrid Elasticsearch matching rank live job postings against your CV.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col font-sans">
        <header className="border-b border-line">
          <nav className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
            <Link href="/" className="font-mono text-sm font-semibold tracking-tight">
              job<span className="text-accent">radar</span>
            </Link>
            <div className="flex items-center gap-4 text-sm">
              <Link href="/demo" className="text-muted hover:text-foreground">Demo</Link>
              <a href={REPO_URL} className="text-muted hover:text-foreground">GitHub</a>
              <UserMenu />
            </div>
          </nav>
        </header>
        <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-10">{children}</main>
        <footer className="border-t border-line py-6 text-center text-xs text-muted">
          Demo runs are capped (one per account, 10 scored jobs, 3 drafts) and deleted after 24 hours. Nothing is ever sent.
        </footer>
      </body>
    </html>
  );
}
