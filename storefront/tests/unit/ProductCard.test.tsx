import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProductCard } from "@/presentation/components/ProductCard";
import type { Product } from "@/domain/types";

function makeProduct(overrides: Partial<Product> = {}): Product {
  return {
    id: "1",
    name: "Widget",
    slug: "widget",
    description: null,
    price: "19.99",
    compare_at_price: null,
    images: [],
    category_id: null,
    in_stock: true,
    ...overrides,
  };
}

describe("ProductCard", () => {
  it("renders the product name and price, linked to its detail page", () => {
    render(<ProductCard product={makeProduct()} />);
    expect(screen.getByText("Widget")).toBeInTheDocument();
    expect(screen.getByText("$19.99")).toBeInTheDocument();
    expect(screen.getByRole("link")).toHaveAttribute("href", "/products/widget");
  });

  it("shows the compare-at price when present", () => {
    render(<ProductCard product={makeProduct({ compare_at_price: "29.99" })} />);
    expect(screen.getByText("$29.99")).toBeInTheDocument();
  });

  it("shows an out-of-stock badge when the product has no stock", () => {
    render(<ProductCard product={makeProduct({ in_stock: false })} />);
    expect(screen.getByText("Out of stock")).toBeInTheDocument();
  });
});
