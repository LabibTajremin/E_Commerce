"use client";

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import type { ApiClient } from "@/application/interfaces/ApiClient";
import { AuthContext, type AuthContextValue } from "@/application/use-cases/useAuth";
import { tokenStore } from "@/infrastructure/api/tokenStore";
import { AUTH_EXPIRED_EVENT } from "@/infrastructure/api/httpClient";
import type { TokenPair } from "@/domain/types";

export function AuthProvider({
  client,
  children,
}: {
  client: ApiClient;
  children: ReactNode;
}) {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsAuthenticated(Boolean(tokenStore.getAccessToken()));
    setIsLoading(false);

    const onExpired = () => {
      setIsAuthenticated(false);
      router.push("/login");
    };
    window.addEventListener(AUTH_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, onExpired);
  }, [router]);

  const login = useCallback(
    async (email: string, password: string) => {
      const tokens = await client.post<TokenPair>("/api/v1/admin/auth/login", {
        email,
        password,
      });
      tokenStore.setTokens(tokens.access_token, tokens.refresh_token);
      setIsAuthenticated(true);
    },
    [client],
  );

  const logout = useCallback(async () => {
    const refreshToken = tokenStore.getRefreshToken();
    try {
      await client.post("/api/v1/admin/auth/logout", { refresh_token: refreshToken });
    } finally {
      tokenStore.clear();
      setIsAuthenticated(false);
      router.push("/login");
    }
  }, [client, router]);

  const value = useMemo<AuthContextValue>(
    () => ({ isAuthenticated, isLoading, login, logout }),
    [isAuthenticated, isLoading, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
