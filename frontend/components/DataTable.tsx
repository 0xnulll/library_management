"use client";

import { type ReactNode } from "react";

export function TableSkeleton({ cols, rows = 5 }: { cols: number; rows?: number }) {
  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <table className="w-full text-sm">
        <tbody>
          {Array.from({ length: rows }).map((_, i) => (
            <tr key={i} className="border-t border-slate-100 first:border-t-0">
              {Array.from({ length: cols }).map((_, j) => (
                <td key={j} className="px-3 py-3">
                  <div className="h-4 animate-pulse rounded bg-slate-100" />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── column definition ────────────────────────────────────────────────────────

export interface Column<T> {
  header: string;
  className?: string;
  render: (row: T) => ReactNode;
}

// ─── pagination ───────────────────────────────────────────────────────────────

export interface PaginationState {
  page: number;
  pageSize: number;
}

/**
 * Server-side paginator – does NOT need a total count.
 * Detects the last page by whether the server returned fewer rows than pageSize.
 */
export function ServerPaginator({
  page,
  pageSize,
  hasMore,
  onChange,
}: {
  page: number;
  pageSize: number;
  hasMore: boolean;
  onChange: (p: PaginationState) => void;
}) {
  return (
    <div className="flex items-center justify-between px-3 py-2 text-xs text-slate-600">
      <span>Page {page}</span>
      <div className="flex items-center gap-1">
        <button
          onClick={() => onChange({ page: page - 1, pageSize })}
          disabled={page <= 1}
          className="min-w-[24px] rounded border border-slate-300 px-2 py-0.5 hover:bg-slate-100 disabled:opacity-40"
        >
          ‹ Prev
        </button>
        <button
          onClick={() => onChange({ page: page + 1, pageSize })}
          disabled={!hasMore}
          className="min-w-[24px] rounded border border-slate-300 px-2 py-0.5 hover:bg-slate-100 disabled:opacity-40"
        >
          Next ›
        </button>
        <select
          value={pageSize}
          onChange={(e) => onChange({ page: 1, pageSize: Number(e.target.value) })}
          className="ml-2 rounded border border-slate-300 px-1 py-0.5"
        >
          {[10, 25, 50].map((n) => (
            <option key={n} value={n}>{n} / page</option>
          ))}
        </select>
      </div>
    </div>
  );
}

interface PaginatorProps {
  page: number;
  pageSize: number;
  total: number;
  onChange: (p: PaginationState) => void;
}

export function Paginator({ page, pageSize, total, onChange }: PaginatorProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const pages = buildPageList(page, totalPages);

  return (
    <div className="flex items-center justify-between px-3 py-2 text-sm text-slate-600">
      <span>
        {total === 0
          ? "No results"
          : `${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, total)} of ${total}`}
      </span>
      <div className="flex items-center gap-1">
        <PageBtn
          label="‹"
          disabled={page <= 1}
          onClick={() => onChange({ page: page - 1, pageSize })}
        />
        {pages.map((p, i) =>
          p === "…" ? (
            <span key={`gap-${i}`} className="px-1">
              …
            </span>
          ) : (
            <PageBtn
              key={p}
              label={String(p)}
              active={p === page}
              disabled={false}
              onClick={() => onChange({ page: p as number, pageSize })}
            />
          ),
        )}
        <PageBtn
          label="›"
          disabled={page >= totalPages}
          onClick={() => onChange({ page: page + 1, pageSize })}
        />
        <select
          value={pageSize}
          onChange={(e) => onChange({ page: 1, pageSize: Number(e.target.value) })}
          className="ml-2 rounded border border-slate-300 px-1 py-0.5 text-xs"
        >
          {[10, 25, 50].map((n) => (
            <option key={n} value={n}>
              {n} / page
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

function PageBtn({
  label,
  active,
  disabled,
  onClick,
}: {
  label: string;
  active?: boolean;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={[
        "min-w-[28px] rounded px-1.5 py-0.5 text-xs",
        active
          ? "bg-slate-900 text-white"
          : "border border-slate-300 hover:bg-slate-100 disabled:opacity-40",
      ].join(" ")}
    >
      {label}
    </button>
  );
}

function buildPageList(current: number, total: number): (number | "…")[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const pages: (number | "…")[] = [1];
  if (current > 3) pages.push("…");
  for (let p = Math.max(2, current - 1); p <= Math.min(total - 1, current + 1); p++)
    pages.push(p);
  if (current < total - 2) pages.push("…");
  pages.push(total);
  return pages;
}

// ─── DataTable ────────────────────────────────────────────────────────────────

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string | number;
  loading?: boolean;
  emptyMessage?: string;
  /** When provided, renders pagination controls below the table */
  pagination?: {
    page: number;
    pageSize: number;
    total: number;
    onChange: (p: PaginationState) => void;
  };
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  loading,
  emptyMessage = "No data.",
  pagination,
}: DataTableProps<T>) {
  if (loading) return <TableSkeleton cols={columns.length} />;

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-left text-slate-600">
          <tr>
            {columns.map((col) => (
              <th key={col.header} className={["px-3 py-2 font-medium", col.className].join(" ")}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-3 py-8 text-center text-slate-400"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr key={rowKey(row)} className="border-t border-slate-100 hover:bg-slate-50/50">
                {columns.map((col) => (
                  <td key={col.header} className={["px-3 py-2", col.className].join(" ")}>
                    {col.render(row)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
      {pagination && rows.length > 0 && (
        <div className="border-t border-slate-100">
          <Paginator {...pagination} />
        </div>
      )}
    </div>
  );
}
