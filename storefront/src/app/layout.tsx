import type { Metadata } from "next";
import type { ReactNode } from "react";
import { notFound } from "next/navigation";

import { ApiError } from "@/application/interfaces/ApiClient";
import { serverFetch } from "@/infrastructure/api/serverApi";
import { AppProviders } from "@/presentation/providers/AppProviders";
import { ThemeStyle } from "@/presentation/components/ThemeStyle";
import { Header } from "@/presentation/components/Header";
import type { StoreSettings } from "@/domain/types";

import "./globals.css";

async function loadStoreSettings(): Promise<StoreSettings> {
  try {
    return await serverFetch<StoreSettings>("/api/v1/storefront/store");
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }
}

export async function generateMetadata(): Promise<Metadata> {
  const settings = await loadStoreSettings();
  return {
    title: settings.store_name,
    icons: settings.favicon_url ? [{ url: settings.favicon_url }] : undefined,
  };
}

export default async function RootLayout({ children }: { children: ReactNode }) {
  const settings = await loadStoreSettings();

  return (
    <html lang="en">
      <head>
        <ThemeStyle settings={settings} />
      </head>
      <body>
        <AppProviders>
          <Header settings={settings} />
          {children}
        </AppProviders>
      </body>
    </html>
  );
}
