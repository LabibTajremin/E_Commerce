import { act, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "@/presentation/providers/AuthProvider";
import { useAuth } from "@/application/use-cases/useAuth";
import { tokenStore } from "@/infrastructure/api/tokenStore";

import { fakeApiClient } from "./fakeApiClient";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: push }),
}));

function Probe() {
  const { isAuthenticated, isLoading, login, logout } = useAuth();
  return (
    <div>
      <span data-testid="status">
        {isLoading ? "loading" : isAuthenticated ? "authed" : "anon"}
      </span>
      <button onClick={() => void login("a@b.com", "hunter22")}>login</button>
      <button onClick={() => void logout()}>logout</button>
    </div>
  );
}

describe("AuthProvider", () => {
  beforeEach(() => {
    tokenStore.clear();
    push.mockClear();
  });

  it("starts unauthenticated when there is no stored token", async () => {
    const client = fakeApiClient();
    render(
      <AuthProvider client={client}>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("anon"));
  });

  it("becomes authenticated after a successful login and stores tokens", async () => {
    const post = vi.fn().mockResolvedValue({
      access_token: "access-1",
      refresh_token: "refresh-1",
      token_type: "bearer",
    });
    const client = fakeApiClient({ post });

    render(
      <AuthProvider client={client}>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("anon"));

    await act(async () => {
      screen.getByText("login").click();
    });

    expect(post).toHaveBeenCalledWith("/api/v1/admin/auth/login", {
      email: "a@b.com",
      password: "hunter22",
    });
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("authed"));
    expect(tokenStore.getAccessToken()).toBe("access-1");
  });

  it("clears tokens and redirects to /login on logout", async () => {
    tokenStore.setTokens("access-1", "refresh-1");
    const post = vi.fn().mockResolvedValue(undefined);
    const client = fakeApiClient({ post });

    render(
      <AuthProvider client={client}>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("authed"));

    await act(async () => {
      screen.getByText("logout").click();
    });

    expect(tokenStore.getAccessToken()).toBeNull();
    expect(push).toHaveBeenCalledWith("/login");
  });
});
