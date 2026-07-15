import { serverFetch } from "@/infrastructure/api/serverApi";
import { ProductCard } from "@/presentation/components/ProductCard";
import { CategoryFilter } from "@/presentation/components/CategoryFilter";
import type { Category, ProductPage } from "@/domain/types";

import styles from "./page.module.css";

interface ProductsPageProps {
  searchParams: Promise<{ category?: string; search?: string }>;
}

async function loadCategories(): Promise<{ items: Category[] }> {
  return serverFetch<{ items: Category[] }>("/api/v1/storefront/categories");
}

async function loadProducts(categoryId?: string, search?: string): Promise<ProductPage> {
  const params = new URLSearchParams({ limit: "48" });
  if (categoryId) params.set("category_id", categoryId);
  if (search) params.set("search", search);
  return serverFetch<ProductPage>(`/api/v1/storefront/products?${params.toString()}`);
}

export default async function ProductsPage({ searchParams }: ProductsPageProps) {
  const { category, search } = await searchParams;
  const [{ items: categories }, products] = await Promise.all([
    loadCategories(),
    loadProducts(category, search),
  ]);

  return (
    <main className={styles.main}>
      <aside className={styles.sidebar}>
        <CategoryFilter categories={categories} activeCategoryId={category} />
      </aside>
      <section className={styles.content}>
        <form className={styles.search} action="/products" method="get">
          {category ? <input type="hidden" name="category" value={category} /> : null}
          <input type="search" name="search" placeholder="Search products" defaultValue={search} />
          <button type="submit">Search</button>
        </form>

        <div className={styles.grid}>
          {products.items.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
        {products.items.length === 0 ? <p>No products found.</p> : null}
      </section>
    </main>
  );
}
