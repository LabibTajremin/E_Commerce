"use client";

import { useEffect, useState, type ChangeEvent } from "react";

import { httpClient } from "@/infrastructure/api/httpClient";
import {
  selectTheme,
  toggleSection,
  updateBranding,
  uploadStoreImage,
  useStoreSettings,
  useThemes,
} from "@/application/use-cases/useStoreSettings";
import { ApiError } from "@/application/interfaces/ApiClient";

import styles from "./page.module.css";

export default function BrandingPage() {
  const { data: settings, isLoading, error, refetch } = useStoreSettings(httpClient);
  const { data: themes } = useThemes(httpClient);

  const [storeName, setStoreName] = useState("");
  const [primaryColor, setPrimaryColor] = useState("#111827");
  const [accentColor, setAccentColor] = useState("#2563eb");
  const [fontChoice, setFontChoice] = useState("Inter");
  const [announcement, setAnnouncement] = useState("");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (settings) {
      setStoreName(settings.store_name);
      setPrimaryColor(settings.primary_color);
      setAccentColor(settings.accent_color);
      setFontChoice(settings.font_choice);
      setAnnouncement(settings.announcement_bar_text ?? "");
    }
  }, [settings]);

  async function handleSave() {
    setSaveError(null);
    setIsSaving(true);
    try {
      await updateBranding(httpClient, {
        store_name: storeName,
        primary_color: primaryColor,
        accent_color: accentColor,
        font_choice: fontChoice,
        announcement_bar_text: announcement || null,
      });
      refetch();
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : "Could not save branding");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleThemeSelect(themeId: string) {
    await selectTheme(httpClient, themeId);
    refetch();
  }

  async function handleSectionToggle(section: string, enabled: boolean) {
    await toggleSection(httpClient, section, enabled);
    refetch();
  }

  async function handleImageUpload(
    kind: "logo" | "favicon" | "banner",
    event: ChangeEvent<HTMLInputElement>,
  ) {
    const file = event.target.files?.[0];
    if (!file) return;
    await uploadStoreImage(kind, file);
    refetch();
    event.target.value = "";
  }

  if (isLoading) return <p>Loading...</p>;
  if (error) return <p>{error}</p>;

  return (
    <section>
      <h1>Storefront branding</h1>
      <div className={styles.grid}>
        <div className={styles.formColumn}>
          <div className={styles.field}>
            <label>Store name</label>
            <input value={storeName} onChange={(e) => setStoreName(e.target.value)} />
          </div>
          <div className={styles.colorRow}>
            <div className={styles.field}>
              <label>Primary color</label>
              <input
                type="color"
                value={primaryColor}
                onChange={(e) => setPrimaryColor(e.target.value)}
              />
            </div>
            <div className={styles.field}>
              <label>Accent color</label>
              <input
                type="color"
                value={accentColor}
                onChange={(e) => setAccentColor(e.target.value)}
              />
            </div>
          </div>
          <div className={styles.field}>
            <label>Font</label>
            <input value={fontChoice} onChange={(e) => setFontChoice(e.target.value)} />
          </div>
          <div className={styles.field}>
            <label>Announcement bar text</label>
            <input value={announcement} onChange={(e) => setAnnouncement(e.target.value)} />
          </div>
          {saveError ? <p className={styles.error}>{saveError}</p> : null}
          <button className={styles.save} onClick={handleSave} disabled={isSaving}>
            {isSaving ? "Saving..." : "Save branding"}
          </button>

          <h2>Theme</h2>
          <div className={styles.themeList}>
            {(themes ?? []).map((theme) => (
              <button
                key={theme.id}
                className={theme.id === settings?.theme_id ? styles.themeActive : styles.theme}
                onClick={() => handleThemeSelect(theme.id)}
              >
                {theme.name}
              </button>
            ))}
          </div>

          <h2>Sections</h2>
          <div className={styles.sections}>
            {settings
              ? Object.entries(settings.enabled_sections).map(([section, enabled]) => (
                  <label key={section} className={styles.sectionToggle}>
                    <input
                      type="checkbox"
                      checked={enabled}
                      onChange={(e) => handleSectionToggle(section, e.target.checked)}
                    />
                    {section}
                  </label>
                ))
              : null}
          </div>

          <h2>Images</h2>
          <div className={styles.field}>
            <label>Logo</label>
            <input type="file" accept="image/*" onChange={(e) => handleImageUpload("logo", e)} />
          </div>
          <div className={styles.field}>
            <label>Favicon</label>
            <input
              type="file"
              accept="image/*"
              onChange={(e) => handleImageUpload("favicon", e)}
            />
          </div>
          <div className={styles.field}>
            <label>Add banner image</label>
            <input
              type="file"
              accept="image/*"
              onChange={(e) => handleImageUpload("banner", e)}
            />
          </div>
        </div>

        <div className={styles.previewColumn}>
          <h2>Live preview</h2>
          <div
            className={styles.preview}
            style={
              {
                "--preview-primary": primaryColor,
                "--preview-accent": accentColor,
                "--preview-font": fontChoice,
              } as React.CSSProperties
            }
          >
            {announcement ? <div className={styles.previewAnnouncement}>{announcement}</div> : null}
            <div className={styles.previewHeader}>
              {settings?.logo_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={settings.logo_url} alt="Logo" className={styles.previewLogo} />
              ) : null}
              <span className={styles.previewStoreName}>{storeName || "Your Store"}</span>
            </div>
            <div className={styles.previewHero}>
              <button className={styles.previewCta}>Shop now</button>
            </div>
            {settings && settings.banner_images.length > 0 ? (
              <div className={styles.previewBanners}>
                {settings.banner_images.map((url) => (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img key={url} src={url} alt="Banner" className={styles.previewBanner} />
                ))}
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </section>
  );
}
