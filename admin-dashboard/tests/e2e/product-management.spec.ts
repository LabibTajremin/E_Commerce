import { expect, test } from "@playwright/test";

/**
 * Critical flow: sign in as a tenant owner, create a product, and see it in
 * the list. Requires a live backend at BACKEND_BASE_URL with the tenant's
 * subdomain resolving to this admin-dashboard's own host (see
 * infrastructure/api/apiBaseUrl.ts) — e.g. both served under *.localhost so
 * the browser's Host header threads the tenant through on every API call.
 *
 * There's no registration UI in the dashboard (platform tenants are
 * provisioned out-of-band), so the fixture tenant/owner are created directly
 * against the backend's registration endpoint before the UI flow starts.
 */
const BACKEND_BASE_URL = process.env.BACKEND_BASE_URL ?? "http://localhost:8000";

test("owner logs in, creates a product, and sees it in the list", async ({
  page,
  request,
}) => {
  const subdomain = `e2e-admin-${Date.now()}`;
  const email = `owner@${subdomain}.com`;
  const password = "hunter22!!";

  const registerResponse = await request.post(`${BACKEND_BASE_URL}/api/v1/auth/register`, {
    data: {
      tenant_name: subdomain,
      subdomain,
      owner_email: email,
      owner_password: password,
    },
    headers: { host: "platform.localhost" },
  });
  expect(registerResponse.ok()).toBeTruthy();

  await page.goto(`http://${subdomain}.localhost:3000/login`);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page).toHaveURL(`http://${subdomain}.localhost:3000/`);

  await page.getByRole("link", { name: "Manage products" }).click();
  await page.getByRole("link", { name: "New product" }).click();

  await page.getByLabel("Name").fill("Playwright Widget");
  await page.getByLabel("Price").fill("19.99");
  await page.getByRole("button", { name: "Create product" }).click();

  await expect(page).toHaveURL(/\/products\//);

  await page.goto(`http://${subdomain}.localhost:3000/products`);
  await expect(page.getByText("Playwright Widget")).toBeVisible();
});
