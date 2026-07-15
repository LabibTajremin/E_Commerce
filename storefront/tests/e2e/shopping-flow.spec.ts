import { expect, test } from "@playwright/test";

/**
 * Critical flow: browse as a guest, add a product to cart, get redirected to
 * sign-in at checkout, register, and land back in the checkout form with the
 * cart items carried over (see CustomerAuthProvider's guest-cart transfer).
 * Requires a live backend + this app's dev server, both under *.localhost.
 */
const BACKEND_BASE_URL = process.env.BACKEND_BASE_URL ?? "http://localhost:8000";

test("guest adds to cart, then registers at checkout and places an order", async ({
  page,
  request,
}) => {
  const subdomain = `e2e-shop-${Date.now()}`;
  const ownerEmail = `owner@${subdomain}.com`;
  const ownerPassword = "hunter22!!";

  await request.post(`${BACKEND_BASE_URL}/api/v1/auth/register`, {
    data: {
      tenant_name: subdomain,
      subdomain,
      owner_email: ownerEmail,
      owner_password: ownerPassword,
    },
    headers: { host: "platform.localhost" },
  });
  const loginResponse = await request.post(`${BACKEND_BASE_URL}/api/v1/admin/auth/login`, {
    data: { email: ownerEmail, password: ownerPassword },
    headers: { host: `${subdomain}.localhost` },
  });
  const { access_token: adminToken } = await loginResponse.json();

  const productResponse = await request.post(`${BACKEND_BASE_URL}/api/v1/admin/products`, {
    data: { name: "E2E Shirt", price: "25.00", stock_qty: 10 },
    headers: { host: `${subdomain}.localhost`, authorization: `Bearer ${adminToken}` },
  });
  const product = await productResponse.json();
  await request.post(`${BACKEND_BASE_URL}/api/v1/admin/products/bulk-status`, {
    data: { product_ids: [product.id], status: "published" },
    headers: { host: `${subdomain}.localhost`, authorization: `Bearer ${adminToken}` },
  });

  await page.goto(`http://${subdomain}.localhost:3001/products/${product.slug}`);
  await page.getByRole("button", { name: "Add to cart" }).click();
  await expect(page.getByRole("button", { name: "Added!" })).toBeVisible();

  await page.goto(`http://${subdomain}.localhost:3001/checkout`);
  await page.getByRole("link", { name: "Create account" }).click();

  await page.getByLabel("Name").fill("Jane Buyer");
  await page.getByLabel("Email").fill(`buyer@${subdomain}.com`);
  await page.getByLabel("Password").fill("hunter22!!");
  await page.getByRole("button", { name: "Create account" }).click();

  await page.goto(`http://${subdomain}.localhost:3001/cart`);
  await expect(page.getByText("E2E Shirt")).toBeVisible();

  await page.goto(`http://${subdomain}.localhost:3001/checkout`);
  await page.getByLabel("Address line 1").fill("1 Main St");
  await page.getByLabel("City").fill("Metropolis");
  await page.getByLabel("State").fill("CA");
  await page.getByLabel("Postal code").fill("90210");
  await page.getByLabel("Country").fill("US");
  await page.getByRole("button", { name: "Place order" }).click();

  await expect(page).toHaveURL(/\/orders\//);
  await expect(page.getByText("pending")).toBeVisible();
});
