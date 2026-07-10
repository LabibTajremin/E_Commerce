"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError } from "@/application/interfaces/ApiClient";

export interface AsyncState<T> {
  data: T | null;
  isLoading: boolean;
  error: string | null;
}

export function useAsync<T>(fetcher: () => Promise<T>, deps: unknown[]) {
  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    isLoading: true,
    error: null,
  });

  const run = useCallback(() => {
    let cancelled = false;
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    fetcher()
      .then((data) => {
        if (!cancelled) setState({ data, isLoading: false, error: null });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          const message = err instanceof ApiError ? err.message : "Something went wrong";
          setState({ data: null, isLoading: false, error: message });
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => run(), [run]);

  return { ...state, refetch: run };
}
