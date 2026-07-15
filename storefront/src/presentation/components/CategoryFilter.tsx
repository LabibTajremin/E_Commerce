import Link from "next/link";

import type { Category } from "@/domain/types";

import styles from "./CategoryFilter.module.css";

export function CategoryFilter({
  categories,
  activeCategoryId,
}: {
  categories: Category[];
  activeCategoryId?: string;
}) {
  return (
    <nav>
      <ul className={styles.list}>
        <li>
          <Link href="/products" className={!activeCategoryId ? styles.active : undefined}>
            All products
          </Link>
        </li>
        {categories.map((category) => (
          <li key={category.id}>
            <Link
              href={`/products?category=${category.id}`}
              className={activeCategoryId === category.id ? styles.active : undefined}
            >
              {category.name}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
