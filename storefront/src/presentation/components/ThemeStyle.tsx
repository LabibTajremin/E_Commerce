import type { StoreSettings } from "@/domain/types";

const HEX_COLOR = /^#[0-9a-fA-F]{3,8}$/;
// Font family lists may contain letters, numbers, spaces, hyphens, commas, and quotes;
// this store_name-adjacent field is tenant-admin-controlled free text, not backend-validated
// CSS syntax, so it's sanitized before landing in a raw <style> block.
const SAFE_FONT_CHARS = /^[a-zA-Z0-9 ,\-'"]*$/;

function sanitizeColor(value: string, fallback: string): string {
  return HEX_COLOR.test(value) ? value : fallback;
}

function sanitizeFont(value: string, fallback: string): string {
  return SAFE_FONT_CHARS.test(value) && value.trim() ? value : fallback;
}

export function ThemeStyle({ settings }: { settings: StoreSettings }) {
  const primary = sanitizeColor(settings.primary_color, "#111827");
  const accent = sanitizeColor(settings.accent_color, "#2563eb");
  const font = sanitizeFont(settings.font_choice, "Inter");

  const css = `:root {
    --color-primary: ${primary};
    --color-accent: ${accent};
    --font-family: "${font}", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }`;

  return <style dangerouslySetInnerHTML={{ __html: css }} />;
}
