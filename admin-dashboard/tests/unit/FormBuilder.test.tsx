import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { FormBuilder, type FieldConfig } from "@/presentation/components/primitives/FormBuilder";

const fields: FieldConfig[] = [
  { name: "name", label: "Name", type: "text", required: true },
  { name: "featured", label: "Featured", type: "checkbox" },
];

describe("FormBuilder", () => {
  it("renders a labeled input per field and reports changes", () => {
    const onChange = vi.fn();
    render(
      <FormBuilder fields={fields} values={{}} onChange={onChange} onSubmit={vi.fn()} />,
    );

    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Widget" } });
    expect(onChange).toHaveBeenCalledWith("name", "Widget");

    fireEvent.click(screen.getByLabelText("Featured"));
    expect(onChange).toHaveBeenCalledWith("featured", true);
  });

  it("calls onSubmit when the form is submitted", () => {
    const onSubmit = vi.fn();
    render(
      <FormBuilder fields={fields} values={{ name: "Widget" }} onChange={vi.fn()} onSubmit={onSubmit} />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onSubmit).toHaveBeenCalled();
  });

  it("shows the error message when provided", () => {
    render(
      <FormBuilder
        fields={fields}
        values={{}}
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        error="Something broke"
      />,
    );
    expect(screen.getByText("Something broke")).toBeInTheDocument();
  });

  it("disables the submit button while submitting", () => {
    render(
      <FormBuilder
        fields={fields}
        values={{}}
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        isSubmitting
      />,
    );
    expect(screen.getByRole("button", { name: "Saving..." })).toBeDisabled();
  });
});
