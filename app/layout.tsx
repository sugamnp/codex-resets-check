import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Codex Reset Watch",
  description: "Checks whether a credible Codex usage reset has been announced."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
