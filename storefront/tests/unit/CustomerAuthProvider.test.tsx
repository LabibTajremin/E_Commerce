import { act, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CustomerAuthProvider } from "@/presentation/providers/CustomerAuthProvider";
import { useCustomerAuth } from "@/application/use-cases/useCustomerAuth";
import { tokenStore } from "@/infrastructure/api/tokenStore";
import type { Cart } from "@/domain/types";

import { fakeApiClient } from "./fakeApiClient";

function Probe() {
  const { isAuthenticated, isLoading, login, logout, register } = useCustomerAuth();
  return (
    <div>
      <span data-testid="status">
        {isLoading ? "loading" : isAuthenticated ? "authed" : "anon"}
      </span>
      <button onClick={() => void login("a@b.com", "hunter22!!")}>login</button>
      <button onClick={() => void register("a@b.com", "hunter22!!", "A")}>register</button>
      <button onClick={logout}>logout</button>
    </div>
  );
}

describe("CustomerAuthProvider", () => {
  beforeEach(() => {
    tokenStore.clear();
  });

  it("starts unauthenticated with no stored token", async () => {
    render(
      <CustomerAuthProvider client={fakeApiClient()}>
        <Probe />
      </CustomerAuthProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("anon"));
  });

  it("becomes authenticated and stores tokens after login", async () => {
    const emptyCart: Cart = { id: "cart-1", line_items: [] };
    const get = vi.fn().mockResolvedValue(emptyCart);
    const post = vi.fn().mockResolvedValue({
      access_token: "access-1",
      refresh_token: "refresh-1",
      token_type: "bearer",
    });
    const client = fakeApiClient({ get, post });

    render(
      <CustomerAuthProvider client={client}>
        <Probe />
      </CustomerAuthProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("anon"));

    await act(async () => {
      screen.getByText("login").click();
    });

    expect(post).toHaveBeenCalledWith("/api/v1/storefront/customers/login", {
      email: "a@b.com",
      password: "hunter22!!",
    });
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("authed"));
    expect(tokenStore.getAccessToken()).toBe("access-1");
  });

  it("replays guest cart line items under the new customer identity on login", async () => {
    const guestCart: Cart = { id: "cart-1", line_items: [{ product_id: "p1", quantity: 2 }] };
    const get = vi.fn().mockResolvedValue(guestCart);
    const post = vi.fn().mockImplementation((path: string) => {
      if (path === "/api/v1/storefront/customers/login") {
        return Promise.resolve({
          access_token: "access-1",
          refresh_token: "refresh-1",
          token_type: "bearer",
        });
      }
      return Promise.resolve(guestCart);
    });
    const client = fakeApiClient({ get, post });

    render(
      <CustomerAuthProvider client={client}>
        <Probe />
      </CustomerAuthProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("anon"));

    await act(async () => {
      screen.getByText("login").click();
    });

    await waitFor(() =>
      expect(post).toHaveBeenCalledWith("/api/v1/storefront/cart/items", {
        product_id: "p1",
        quantity: 2,
      }),
    );
  });

  it("clears tokens on logout", async () => {
    tokenStore.setTokens("access-1", "refresh-1");
    render(
      <CustomerAuthProvider client={fakeApiClient()}>
        <Probe />
      </CustomerAuthProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("authed"));

    act(() => {
      screen.getByText("logout").click();
    });

    expect(tokenStore.getAccessToken()).toBeNull();
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("anon"));
  });
});
