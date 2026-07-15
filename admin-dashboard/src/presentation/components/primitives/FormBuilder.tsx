"use client";

import type { FormEvent } from "react";

import styles from "./FormBuilder.module.css";

export type FieldType = "text" | "number" | "textarea" | "select" | "checkbox" | "color";

export interface FieldOption {
  label: string;
  value: string;
}

export interface FieldConfig {
  name: string;
  label: string;
  type: FieldType;
  options?: FieldOption[];
  required?: boolean;
  placeholder?: string;
  step?: string;
}

export type FormValues = Record<string, string | number | boolean | null | undefined>;

export interface FormBuilderProps {
  fields: FieldConfig[];
  values: FormValues;
  onChange: (name: string, value: string | number | boolean) => void;
  onSubmit: () => void;
  submitLabel?: string;
  isSubmitting?: boolean;
  error?: string | null;
}

export function FormBuilder({
  fields,
  values,
  onChange,
  onSubmit,
  submitLabel = "Save",
  isSubmitting = false,
  error,
}: FormBuilderProps) {
  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      {fields.map((field) => (
        <div className={styles.field} key={field.name}>
          <label htmlFor={field.name}>{field.label}</label>
          {renderInput(field, values, onChange)}
        </div>
      ))}
      {error ? <p className={styles.error}>{error}</p> : null}
      <button type="submit" className={styles.submit} disabled={isSubmitting}>
        {isSubmitting ? "Saving..." : submitLabel}
      </button>
    </form>
  );
}

function renderInput(
  field: FieldConfig,
  values: FormValues,
  onChange: (name: string, value: string | number | boolean) => void,
) {
  const value = values[field.name];

  if (field.type === "textarea") {
    return (
      <textarea
        id={field.name}
        name={field.name}
        required={field.required}
        placeholder={field.placeholder}
        value={(value as string) ?? ""}
        onChange={(e) => onChange(field.name, e.target.value)}
        rows={4}
      />
    );
  }

  if (field.type === "select") {
    return (
      <select
        id={field.name}
        name={field.name}
        required={field.required}
        value={(value as string) ?? ""}
        onChange={(e) => onChange(field.name, e.target.value)}
      >
        <option value="">Select...</option>
        {field.options?.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    );
  }

  if (field.type === "checkbox") {
    return (
      <input
        id={field.name}
        name={field.name}
        type="checkbox"
        checked={Boolean(value)}
        onChange={(e) => onChange(field.name, e.target.checked)}
      />
    );
  }

  if (field.type === "color") {
    return (
      <input
        id={field.name}
        name={field.name}
        type="color"
        value={(value as string) || "#000000"}
        onChange={(e) => onChange(field.name, e.target.value)}
      />
    );
  }

  return (
    <input
      id={field.name}
      name={field.name}
      type={field.type}
      step={field.step}
      required={field.required}
      placeholder={field.placeholder}
      value={value === null || value === undefined ? "" : String(value)}
      onChange={(e) =>
        onChange(field.name, field.type === "number" ? e.target.valueAsNumber : e.target.value)
      }
    />
  );
}
