import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "DemoBoard",
  description: "Next.js + shadcn/ui + TypeScript 게시판",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="ko"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-muted/40">
        <header className="border-b bg-background">
          <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
            <Link href="/" className="text-lg font-semibold tracking-tight">
              DemoBoard
            </Link>
            <nav className="flex gap-4 text-sm text-muted-foreground">
              <Link href="/" className="hover:text-foreground">
                목록
              </Link>
              <Link href="/posts/new" className="hover:text-foreground">
                글쓰기
              </Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">{children}</main>
        <footer className="py-6 text-center text-xs text-muted-foreground">© DemoBoard</footer>
      </body>
    </html>
  );
}
