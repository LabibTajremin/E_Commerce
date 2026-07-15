"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { httpClient } from "@/infrastructure/api/httpClient";
import { ApiError } from "@/application/interfaces/ApiClient";
import { createProduct } from "@/application/use-cases/useProducts";
import { useCategoryList } from "@/application/use-cases/useCategories";
import { FormBuilder, type FieldConfig, type FormValues } from "@/presentation/components/primitives/FormBuilder";

export default function NewProductPage() {
  const router = useRouter();
  const { data: categories } = useCategoryList(httpClient);
  const [values, setValues] = useState<FormValues>({
    name: "",
    price: "",
    description: "",
    sku: "",
    stock_qty: 0,
    category_id: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fields: FieldConfig[] = [
    { name: "name", label: "Name", type: "text", required: true },
    { name: "price", label: "Price", type: "number", step: "0.01", required: true },
    { name: "description", label: "Description", type: "textarea" },
    { name: "sku", label: "SKU", type: "text" },
    { name: "stock_qty", label: "Stock quantity", type: "number" },
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
      const product = await createProduct(httpClient, {
        name: String(values.name ?? ""),
        price: String(values.price ?? ""),
        description: (values.description as string) || null,
        sku: (values.sku as string) || null,
        stock_qty: Number(values.stock_qty ?? 0),
        category_id: (values.category_id as string) || null,
      });
      router.push(`/products/${product.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create product");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section>
      <h1>New product</h1>
      <FormBuilder
        fields={fields}
        values={values}
        onChange={(name, value) => setValues((prev) => ({ ...prev, [name]: value }))}
        onSubmit={handleSubmit}
        submitLabel="Create product"
        isSubmitting={isSubmitting}
        error={error}
      />
    </section>
  );
}
