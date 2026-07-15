import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/infrastructure/api/httpClient", () => ({
  httpClient: { post: vi.fn() },
  AUTH_EXPIRED_EVENT: "auth:expired",
}));

import { httpClient } from "@/infrastructure/api/httpClient";
import { AddToCartButton } from "@/presentation/components/AddToCartButton";

describe("AddToCartButton", () => {
  it("renders an out-of-stock message and no controls when unavailable", () => {
    render(<AddToCartButton productId="1" inStock={false} />);
    expect(screen.getByText("Out of stock")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("posts the selected quantity to the cart and shows confirmation", async () => {
    const post = vi.mocked(httpClient.post).mockResolvedValue({ id: "cart-1", line_items: [] });
    const user = userEvent.setup();

    render(<AddToCartButton productId="prod-1" inStock />);
    await user.click(screen.getByRole("button", { name: "Add to cart" }));

    await waitFor(() =>
      expect(post).toHaveBeenCalledWith("/api/v1/storefront/cart/items", {
        product_id: "prod-1",
        quantity: 1,
      }),
    );
    expect(await screen.findByRole("button", { name: "Added!" })).toBeInTheDocument();
  });

  it("shows an error message when the request fails", async () => {
    vi.mocked(httpClient.post).mockRejectedValue(new Error("boom"));
    const user = userEvent.setup();

    render(<AddToCartButton productId="prod-1" inStock />);
    await user.click(screen.getByRole("button", { name: "Add to cart" }));

    expect(await screen.findByText("Could not add to cart")).toBeInTheDocument();
  });
});
