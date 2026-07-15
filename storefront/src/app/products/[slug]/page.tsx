import { notFound } from "next/navigation";

import { serverFetch } from "@/infrastructure/api/serverApi";
import { ApiError } from "@/application/interfaces/ApiClient";
import { AddToCartButton } from "@/presentation/components/AddToCartButton";
import type { Product } from "@/domain/types";

import styles from "./page.module.css";

async function loadProduct(slug: string): Promise<Product | null> {
  try {
    return await serverFetch<Product>(`/api/v1/storefront/products/${slug}`);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

export default async function ProductDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const product = await loadProduct(slug);
  if (!product) notFound();

  return (
    <main className={styles.main}>
      <div className={styles.gallery}>
        {product.images[0] ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={product.images[0]} alt={product.name} className={styles.mainImage} />
        ) : (
          <div className={styles.placeholder} />
        )}
        {product.images.length > 1 ? (
          <div className={styles.thumbnails}>
            {product.images.slice(1).map((url) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img key={url} src={url} alt="" className={styles.thumbnail} />
            ))}
          </div>
        ) : null}
      </div>
      <div className={styles.details}>
        <h1>{product.name}</h1>
        <p className={styles.price}>
          ${product.price}
          {product.compare_at_price ? (
            <span className={styles.compareAt}>${product.compare_at_price}</span>
          ) : null}
        </p>
        {product.description ? <p className={styles.description}>{product.description}</p> : null}
        <AddToCartButton productId={product.id} inStock={product.in_stock} />
      </div>
    </main>
  );
}
