import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ThemeStyle } from "@/presentation/components/ThemeStyle";
import type { StoreSettings } from "@/domain/types";

function makeSettings(overrides: Partial<StoreSettings> = {}): StoreSettings {
  return {
    store_name: "Acme",
    logo_url: null,
    favicon_url: null,
    primary_color: "#111827",
    accent_color: "#2563eb",
    font_choice: "Inter",
    banner_images: [],
    announcement_bar_text: null,
    social_links: {},
    enabled_sections: {},
    ...overrides,
  };
}

describe("ThemeStyle", () => {
  it("renders valid hex colors and font names directly", () => {
    const { container } = render(<ThemeStyle settings={makeSettings()} />);
    const css = container.querySelector("style")?.innerHTML ?? "";
    expect(css).toContain("--color-primary: #111827");
    expect(css).toContain("--color-accent: #2563eb");
    expect(css).toContain('"Inter"');
  });

  it("falls back to defaults for invalid colors instead of interpolating them raw", () => {
    const { container } = render(
      <ThemeStyle
        settings={makeSettings({
          primary_color: "not-a-color",
          accent_color: "red; } body { display: none",
        })}
      />,
    );
    const css = container.querySelector("style")?.innerHTML ?? "";
    expect(css).toContain("--color-primary: #111827");
    expect(css).toContain("--color-accent: #2563eb");
    expect(css).not.toContain("display: none");
  });

  it("strips a font value containing CSS injection characters", () => {
    const { container } = render(
      <ThemeStyle settings={makeSettings({ font_choice: 'Arial"; } body { background: red' })} />,
    );
    const css = container.querySelector("style")?.innerHTML ?? "";
    expect(css).toContain('"Inter"');
    expect(css).not.toContain("background: red");
  });
});
