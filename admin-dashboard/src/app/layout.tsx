import type { ReactNode } from "react";

import { AppProviders } from "@/presentation/providers/AppProviders";

import "./globals.css";

export const metadata = {
  title: "Admin Dashboard",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
