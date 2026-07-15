"use client";

import type { ReactNode } from "react";

import { httpClient } from "@/infrastructure/api/httpClient";
import { CustomerAuthProvider } from "@/presentation/providers/CustomerAuthProvider";

export function AppProviders({ children }: { children: ReactNode }) {
  return <CustomerAuthProvider client={httpClient}>{children}</CustomerAuthProvider>;
}
