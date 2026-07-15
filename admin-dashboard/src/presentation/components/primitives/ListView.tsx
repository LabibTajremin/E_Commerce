import type { ReactNode } from "react";

import { DataTable, type Column } from "./DataTable";
import styles from "./ListView.module.css";

export interface ListViewProps<T> {
  title: string;
  columns: Column<T>[];
  rows: T[];
  getRowId: (row: T) => string;
  onRowClick?: (row: T) => void;
  isLoading: boolean;
  error?: string | null;
  actions?: ReactNode;
  emptyMessage?: string;
  pagination?: {
    offset: number;
    limit: number;
    total: number;
    onPrev: () => void;
    onNext: () => void;
  };
}

export function ListView<T>({
  title,
  columns,
  rows,
  getRowId,
  onRowClick,
  isLoading,
  error,
  actions,
  emptyMessage,
  pagination,
}: ListViewProps<T>) {
  return (
    <section className={styles.section}>
      <header className={styles.header}>
        <h1>{title}</h1>
        {actions ? <div className={styles.actions}>{actions}</div> : null}
      </header>

      {error ? <p className={styles.error}>{error}</p> : null}
      {isLoading ? (
        <p className={styles.loading}>Loading...</p>
      ) : (
        <DataTable
          columns={columns}
          rows={rows}
          getRowId={getRowId}
          onRowClick={onRowClick}
          emptyMessage={emptyMessage}
        />
      )}

      {pagination ? (
        <div className={styles.pagination}>
          <button onClick={pagination.onPrev} disabled={pagination.offset === 0}>
            Previous
          </button>
          <span>
            {pagination.total === 0
              ? "0 results"
              : `${pagination.offset + 1}-${Math.min(pagination.offset + pagination.limit, pagination.total)} of ${pagination.total}`}
          </span>
          <button
            onClick={pagination.onNext}
            disabled={pagination.offset + pagination.limit >= pagination.total}
          >
            Next
          </button>
        </div>
      ) : null}
    </section>
  );
}
