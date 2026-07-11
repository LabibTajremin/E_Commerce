import { afterEach, describe, expect, it, vi } from "vitest";

import { resolveApiBaseUrl } from "@/infrastructure/api/apiBaseUrl";

function setHostname(hostname: string) {
  vi.stubGlobal("location", { ...window.location, hostname });
}

describe("resolveApiBaseUrl", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns the configured API URL unchanged when the page has no tenant subdomain", () => {
    setHostname("localhost");
    expect(resolveApiBaseUrl()).toBe("http://localhost:8000");
  });

  it("splices the page's leftmost label onto the configured API host (dev: same base domain)", () => {
    setHostname("acme.localhost");
    expect(resolveApiBaseUrl()).toBe("http://acme.localhost:8000");
  });

  it("splices the tenant label through even when the API lives on an unrelated domain (production)", () => {
    setHostname("acme.admin.yourplatform.com");
    expect(resolveApiBaseUrl()).toBe("http://acme.localhost:8000");
  });

  it("prefers an explicitly passed host over window.location", () => {
    setHostname("should-be-ignored.localhost");
    expect(resolveApiBaseUrl("acme.localhost")).toBe("http://acme.localhost:8000");
  });
});
