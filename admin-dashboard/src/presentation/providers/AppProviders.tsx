"use client";

import type { ReactNode } from "react";

import { httpClient } from "@/infrastructure/api/httpClient";
import { AuthProvider } from "@/presentation/providers/AuthProvider";

export function AppProviders({ children }: { children: ReactNode }) {
  return <AuthProvider client={httpClient}>{children}</AuthProvider>;
}
