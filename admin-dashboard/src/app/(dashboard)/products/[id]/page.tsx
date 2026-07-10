"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { httpClient } from "@/infrastructure/api/httpClient";
import { ApiError } from "@/application/interfaces/ApiClient";
import { deleteProduct, updateProduct, useProduct } from "@/application/use-cases/useProducts";
import { useCategoryList } from "@/application/use-cases/useCategories";
import {
  FormBuilder,
  type FieldConfig,
  type FormValues,
} from "@/presentation/components/primitives/FormBuilder";

export default function EditProductPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const { data: product, isLoading, error: loadError } = useProduct(httpClient, id);
  const { data: categories } = useCategoryList(httpClient);
  const [values, setValues] = useState<FormValues>({});
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (product) {
      setValues({
        name: product.name,
        price: product.price,
        description: product.description ?? "",
        sku: product.sku ?? "",
        category_id: product.category_id ?? "",
      });
    }
  }, [product]);

  const fields: FieldConfig[] = [
    { name: "name", label: "Name", type: "text", required: true },
    { name: "price", label: "Price", type: "number", step: "0.01", required: true },
    { name: "description", label: "Description", type: "textarea" },
    { name: "sku", label: "SKU", type: "text" },
    {
      name: "category_id",
      label: "Category",
      type: "select",
      options: (categories ?? []).map((c) => ({ label: c.name, value: c.id })),
    },
  ];

  async function handleSubmit() {
    setError(null);
    setIsSubmitting(true);
    try {
      await updateProduct(httpClient, id, {
        name: String(values.name ?? ""),
        price: String(values.price ?? ""),
        description: (values.description as string) || null,
        sku: (values.sku as string) || null,
        category_id: (values.category_id as string) || null,
      });
      router.push("/products");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update product");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!window.confirm("Delete this product?")) return;
    await deleteProduct(httpClient, id);
    router.push("/products");
  }

  if (isLoading) return <p>Loading...</p>;
  if (loadError) return <p>{loadError}</p>;

  return (
    <section>
      <h1>Edit product</h1>
      <FormBuilder
        fields={fields}
        values={values}
        onChange={(name, value) => setValues((prev) => ({ ...prev, [name]: value }))}
        onSubmit={handleSubmit}
        submitLabel="Save changes"
        isSubmitting={isSubmitting}
        error={error}
      />
      <button onClick={handleDelete} style={{ marginTop: 16 }}>
        Delete product
      </button>
    </section>
  );
}
