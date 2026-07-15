import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SideMenu, type NavItem } from "@/presentation/components/primitives/SideMenu";

vi.mock("next/navigation", () => ({
  usePathname: () => "/products",
}));

const items: NavItem[] = [
  { label: "Overview", href: "/" },
  { label: "Products", href: "/products" },
];

describe("SideMenu", () => {
  it("renders a link per item", () => {
    render(<SideMenu items={items} />);
    expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "Products" })).toHaveAttribute("href", "/products");
  });

  it("marks the link matching the current pathname as active", () => {
    render(<SideMenu items={items} />);
    const productsLink = screen.getByRole("link", { name: "Products" });
    const overviewLink = screen.getByRole("link", { name: "Overview" });
    expect(productsLink.className).toMatch(/active/);
    expect(overviewLink.className).not.toMatch(/active/);
  });

  it("renders the footer when provided", () => {
    render(<SideMenu items={items} footer={<span>Sign out</span>} />);
    expect(screen.getByText("Sign out")).toBeInTheDocument();
  });
});
