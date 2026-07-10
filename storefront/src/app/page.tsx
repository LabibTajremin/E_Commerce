import Link from "next/link";

import { serverFetch } from "@/infrastructure/api/serverApi";
import { ProductCard } from "@/presentation/components/ProductCard";
import type { ProductPage, StoreSettings } from "@/domain/types";

import styles from "./page.module.css";

async function loadStoreSettings(): Promise<StoreSettings> {
  return serverFetch<StoreSettings>("/api/v1/storefront/store");
}

async function loadFeaturedProducts(): Promise<ProductPage> {
  return serverFetch<ProductPage>("/api/v1/storefront/products?limit=8");
}

export default async function HomePage() {
  const [settings, products] = await Promise.all([loadStoreSettings(), loadFeaturedProducts()]);

  return (
    <main>
      {settings.enabled_sections.hero_banner ? (
        <section className={styles.hero}>
          {settings.banner_images.length > 0 ? (
            <div className={styles.banners}>
              {settings.banner_images.map((url) => (
                // eslint-disable-next-line @next/next/no-img-element
                <img key={url} src={url} alt="" className={styles.bannerImage} />
              ))}
            </div>
          ) : null}
          <div className={styles.heroCopy}>
            <h1>{settings.store_name}</h1>
            <Link href="/products" className={styles.shopButton}>
              Shop now
            </Link>
          </div>
        </section>
      ) : null}

      {settings.enabled_sections.featured_products ? (
        <section className={styles.section}>
          <h2>Featured products</h2>
          <div className={styles.grid}>
            {products.items.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
          {products.items.length === 0 ? <p>No products published yet.</p> : null}
        </section>
      ) : null}

      {settings.enabled_sections.testimonials ? (
        <section className={styles.testimonials}>
          <h2>What our customers say</h2>
          <blockquote>&ldquo;Fast shipping and great quality!&rdquo;</blockquote>
        </section>
      ) : null}

      {settings.enabled_sections.footer ? (
        <footer className={styles.footer}>
          <p>
            &copy; {new Date().getFullYear()} {settings.store_name}
          </p>
          {Object.entries(settings.social_links).length > 0 ? (
            <div className={styles.socialLinks}>
              {Object.entries(settings.social_links).map(([label, url]) => (
                <a key={label} href={url} target="_blank" rel="noreferrer">
                  {label}
                </a>
              ))}
            </div>
          ) : null}
        </footer>
      ) : null}
    </main>
  );
}
