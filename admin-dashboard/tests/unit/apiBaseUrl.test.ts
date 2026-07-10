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

  it("splices the page's subdomain onto the configured API host", () => {
    setHostname("acme.localhost");
    expect(resolveApiBaseUrl()).toBe("http://acme.localhost:8000");
  });

  it("leaves the API URL unchanged for an unrelated host", () => {
    setHostname("example.com");
    expect(resolveApiBaseUrl()).toBe("http://localhost:8000");
  });
});
