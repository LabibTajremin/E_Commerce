"use client";

import { useEffect, useState } from "react";

import type { ApiClient } from "@/application/interfaces/ApiClient";

interface HealthResponse {
  status: string;
}

export function useHealthCheck(client: ApiClient) {
  const [status, setStatus] = useState<"loading" | "ok" | "error">("loading");

  useEffect(() => {
    let cancelled = false;
    client
      .get<HealthResponse>("/health")
      .then((res) => {
        if (!cancelled) setStatus(res.status === "ok" ? "ok" : "error");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [client]);

  return status;
}
