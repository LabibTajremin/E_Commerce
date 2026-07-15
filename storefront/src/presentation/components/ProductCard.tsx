import Link from "next/link";

import type { Product } from "@/domain/types";

import styles from "./ProductCard.module.css";

export function ProductCard({ product }: { product: Product }) {
  return (
    <Link href={`/products/${product.slug}`} className={styles.card}>
      <div className={styles.imageWrapper}>
        {product.images[0] ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={product.images[0]} alt={product.name} className={styles.image} />
        ) : (
          <div className={styles.placeholder} />
        )}
      </div>
      <div className={styles.body}>
        <h3>{product.name}</h3>
        <p className={styles.price}>
          ${product.price}
          {product.compare_at_price ? (
            <span className={styles.compareAt}>${product.compare_at_price}</span>
          ) : null}
        </p>
        {!product.in_stock ? <span className={styles.outOfStock}>Out of stock</span> : null}
      </div>
    </Link>
  );
}
