import { expect, test } from "@playwright/test";

/**
 * DoD: two tenant subdomains render distinctly from the same storefront
 * codebase. Provisions two tenants directly against the backend (register +
 * admin login + branding PATCH), then loads each tenant's storefront root
 * and asserts the page title and the --color-primary CSS variable differ.
 */
const BACKEND_BASE_URL = process.env.BACKEND_BASE_URL ?? "http://localhost:8000";

async function provisionTenant(
  request: import("@playwright/test").APIRequestContext,
  subdomain: string,
  storeName: string,
  primaryColor: string,
) {
  const email = `owner@${subdomain}.com`;
  const password = "hunter22!!";

  const registerResponse = await request.post(`${BACKEND_BASE_URL}/api/v1/auth/register`, {
    data: { tenant_name: subdomain, subdomain, owner_email: email, owner_password: password },
    headers: { host: "platform.localhost" },
  });
  expect(registerResponse.ok()).toBeTruthy();

  const loginResponse = await request.post(`${BACKEND_BASE_URL}/api/v1/admin/auth/login`, {
    data: { email, password },
    headers: { host: `${subdomain}.localhost` },
  });
  const { access_token } = await loginResponse.json();

  const brandingResponse = await request.patch(
    `${BACKEND_BASE_URL}/api/v1/admin/store-settings`,
    {
      data: { store_name: storeName, primary_color: primaryColor },
      headers: { host: `${subdomain}.localhost`, authorization: `Bearer ${access_token}` },
    },
  );
  expect(brandingResponse.ok()).toBeTruthy();
}

test("two tenant subdomains render distinct branding from the same codebase", async ({
  page,
  request,
}) => {
  const suffix = Date.now();
  const tenantA = `e2e-theme-a-${suffix}`;
  const tenantB = `e2e-theme-b-${suffix}`;

  await provisionTenant(request, tenantA, "Acme Outfitters", "#1d4ed8");
  await provisionTenant(request, tenantB, "Bramble & Co", "#b91c1c");

  await page.goto(`http://${tenantA}.localhost:3001/`);
  await expect(page).toHaveTitle("Acme Outfitters");
  const colorA = await page.evaluate(() =>
    getComputedStyle(document.documentElement).getPropertyValue("--color-primary").trim(),
  );
  expect(colorA).toBe("#1d4ed8");

  await page.goto(`http://${tenantB}.localhost:3001/`);
  await expect(page).toHaveTitle("Bramble & Co");
  const colorB = await page.evaluate(() =>
    getComputedStyle(document.documentElement).getPropertyValue("--color-primary").trim(),
  );
  expect(colorB).toBe("#b91c1c");

  expect(colorA).not.toBe(colorB);
});
