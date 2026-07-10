"use client";

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import type { ApiClient } from "@/application/interfaces/ApiClient";
import {
  CustomerAuthContext,
  type CustomerAuthContextValue,
} from "@/application/use-cases/useCustomerAuth";
import { tokenStore } from "@/infrastructure/api/tokenStore";
import { AUTH_EXPIRED_EVENT } from "@/infrastructure/api/httpClient";
import type { Cart, TokenPair } from "@/domain/types";

export function CustomerAuthProvider({
  client,
  children,
}: {
  client: ApiClient;
  children: ReactNode;
}) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsAuthenticated(Boolean(tokenStore.getAccessToken()));
    setIsLoading(false);

    const onExpired = () => setIsAuthenticated(false);
    window.addEventListener(AUTH_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, onExpired);
  }, []);

  const applyTokensAndTransferGuestCart = useCallback(
    async (tokens: TokenPair) => {
      // Cart resolution prioritizes the bearer token over the guest session
      // id (see backend get_cart_identity), so items added anonymously
      // would otherwise be orphaned the moment the customer logs in. Read
      // the guest cart *before* switching identity, then replay it under
      // the now-authenticated customer.
      let guestCart: Cart | null = null;
      try {
        guestCart = await client.get<Cart>("/api/v1/storefront/cart");
      } catch {
        guestCart = null;
      }

      tokenStore.setTokens(tokens.access_token, tokens.refresh_token);
      setIsAuthenticated(true);

      for (const item of guestCart?.line_items ?? []) {
        await client.post("/api/v1/storefront/cart/items", {
          product_id: item.product_id,
          quantity: item.quantity,
        });
      }
    },
    [client],
  );

  const register = useCallback(
    async (email: string, password: string, name: string) => {
      const tokens = await client.post<TokenPair>("/api/v1/storefront/customers/register", {
        email,
        password,
        name,
      });
      await applyTokensAndTransferGuestCart(tokens);
    },
    [client, applyTokensAndTransferGuestCart],
  );

  const login = useCallback(
    async (email: string, password: string) => {
      const tokens = await client.post<TokenPair>("/api/v1/storefront/customers/login", {
        email,
        password,
      });
      await applyTokensAndTransferGuestCart(tokens);
    },
    [client, applyTokensAndTransferGuestCart],
  );

  const logout = useCallback(() => {
    tokenStore.clear();
    setIsAuthenticated(false);
  }, []);

  const value = useMemo<CustomerAuthContextValue>(
    () => ({ isAuthenticated, isLoading, register, login, logout }),
    [isAuthenticated, isLoading, register, login, logout],
  );

  return <CustomerAuthContext.Provider value={value}>{children}</CustomerAuthContext.Provider>;
}
