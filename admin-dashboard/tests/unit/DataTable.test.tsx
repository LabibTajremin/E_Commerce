import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DataTable, type Column } from "@/presentation/components/primitives/DataTable";

interface Row {
  id: string;
  name: string;
}

const columns: Column<Row>[] = [
  { key: "name", header: "Name" },
  { key: "shout", header: "Shout", render: (row) => row.name.toUpperCase() },
];

describe("DataTable", () => {
  it("renders the empty message when there are no rows", () => {
    render(<DataTable columns={columns} rows={[]} getRowId={(r) => r.id} />);
    expect(screen.getByText("No results")).toBeInTheDocument();
  });

  it("renders a row per item using column render functions", () => {
    render(
      <DataTable
        columns={columns}
        rows={[{ id: "1", name: "widget" }]}
        getRowId={(r) => r.id}
      />,
    );
    expect(screen.getByText("widget")).toBeInTheDocument();
    expect(screen.getByText("WIDGET")).toBeInTheDocument();
  });

  it("calls onRowClick with the clicked row", () => {
    const onRowClick = vi.fn();
    render(
      <DataTable
        columns={columns}
        rows={[{ id: "1", name: "widget" }]}
        getRowId={(r) => r.id}
        onRowClick={onRowClick}
      />,
    );
    fireEvent.click(screen.getByText("widget"));
    expect(onRowClick).toHaveBeenCalledWith({ id: "1", name: "widget" });
  });
});
