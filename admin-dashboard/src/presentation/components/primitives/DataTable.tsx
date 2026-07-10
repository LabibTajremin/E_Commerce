import type { ReactNode } from "react";

import styles from "./DataTable.module.css";

export interface Column<T> {
  key: string;
  header: string;
  render?: (row: T) => ReactNode;
}

export interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  getRowId: (row: T) => string;
  onRowClick?: (row: T) => void;
  emptyMessage?: string;
}

export function DataTable<T>({
  columns,
  rows,
  getRowId,
  onRowClick,
  emptyMessage = "No results",
}: DataTableProps<T>) {
  if (rows.length === 0) {
    return <p className={styles.empty}>{emptyMessage}</p>;
  }

  return (
    <table className={styles.table}>
      <thead>
        <tr>
          {columns.map((column) => (
            <th key={column.key}>{column.header}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr
            key={getRowId(row)}
            onClick={onRowClick ? () => onRowClick(row) : undefined}
            className={onRowClick ? styles.clickableRow : undefined}
          >
            {columns.map((column) => (
              <td key={column.key}>
                {column.render ? column.render(row) : String((row as Record<string, unknown>)[column.key] ?? "")}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
