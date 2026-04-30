"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { authMetadata, books, loans, members, rpcMessage } from "@/lib/grpc";
import { requireMin, requireText } from "@/lib/validate";
import { ServerPaginator, type PaginationState } from "@/components/DataTable";
import type { Book } from "@/lib/proto/book";
import type { Member } from "@/lib/proto/member";

// ─── page ─────────────────────────────────────────────────────────────────────

export default function BooksPage() {
  // search is committed on Enter / Search button so each keystroke doesn't fire a request
  const [draftQuery, setDraftQuery] = useState("");
  const [query, setQuery] = useState("");

  const [items, setItems] = useState<Book[]>([]);
  const [memberList, setMemberList] = useState<Member[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busyBorrowId, setBusyBorrowId] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);

  const [createOpen, setCreateOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [pagination, setPagination] = useState<PaginationState>({ page: 1, pageSize: 10 });

  const load = useCallback(
    async (pg: PaginationState, q: string) => {
      setLoading(true);
      setPageError(null);
      try {
        const meta = authMetadata();
        const offset = (pg.page - 1) * pg.pageSize;
        const [b, m] = await Promise.all([
          books.SearchBooks(
            { query: q, pagination: { limit: pg.pageSize, offset } },
            meta,
          ),
          // members are reference data for the borrow dropdown — load once per page visit
          memberList.length === 0
            ? members.ListMembers({ pagination: { limit: 200, offset: 0 } }, meta)
            : Promise.resolve({ members: memberList }),
        ]);
        setItems(b.books);
        setHasMore(b.books.length === pg.pageSize);
        if (memberList.length === 0) setMemberList((m as { members: Member[] }).members);
      } catch (err) {
        setPageError(rpcMessage(err, "failed to load"));
      } finally {
        setLoading(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [memberList.length],
  );

  // refetch whenever page/size/query changes
  useEffect(() => {
    load(pagination, query);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pagination, query]);

  function commitSearch() {
    const q = draftQuery.trim();
    setQuery(q);
    setPagination((p) => ({ ...p, page: 1 }));
  }

  function handlePaginationChange(p: PaginationState) {
    setEditingId(null);
    setPagination(p);
  }

  async function borrow(book: Book, memberId: number) {
    if (!memberId) return;
    setBusyBorrowId(book.id);
    setPageError(null);
    setMessage(null);
    try {
      await loans.Borrow({ bookId: book.id, memberId, days: 0 }, authMetadata());
      setMessage(`Lent "${book.title}".`);
      load(pagination, query);
    } catch (err) {
      setPageError(rpcMessage(err, "borrow failed"));
    } finally {
      setBusyBorrowId(null);
    }
  }

  return (
    <div className="space-y-4">
      {/* toolbar */}
      <div className="flex flex-wrap items-center gap-2">
        <input
          value={draftQuery}
          onChange={(e) => setDraftQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && commitSearch()}
          placeholder="Search by title, author, or ISBN…"
          className="flex-1 min-w-[180px] rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <button
          onClick={commitSearch}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800"
        >
          Search
        </button>
        <button
          onClick={() => { setCreateOpen((v) => !v); setEditingId(null); }}
          className="rounded-md border border-slate-300 px-4 py-2 text-sm hover:bg-slate-100"
        >
          {createOpen ? "Close" : "Add book"}
        </button>
      </div>

      {createOpen && (
        <BookCreateForm
          onDone={() => { setCreateOpen(false); load(pagination, query); }}
          onCancel={() => setCreateOpen(false)}
        />
      )}

      {message && (
        <p className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{message}</p>
      )}
      {pageError && (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{pageError}</p>
      )}

      {/* table */}
      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        {loading ? (
          <RowSkeleton cols={6} />
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-slate-600">
              <tr>
                <th className="px-3 py-2 font-medium">Title</th>
                <th className="px-3 py-2 font-medium">Author</th>
                <th className="px-3 py-2 font-medium">ISBN</th>
                <th className="px-3 py-2 font-medium">Copies</th>
                <th className="px-3 py-2 font-medium">Borrow</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              {items.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-3 py-8 text-center text-slate-400">
                    No books found.
                  </td>
                </tr>
              )}
              {items.map((b) =>
                editingId === b.id ? (
                  <BookEditRow
                    key={b.id}
                    book={b}
                    onSaved={() => { setEditingId(null); load(pagination, query); }}
                    onCancel={() => setEditingId(null)}
                  />
                ) : (
                  <tr key={b.id} className="border-t border-slate-100 hover:bg-slate-50/50">
                    <td className="px-3 py-2 font-medium">{b.title}</td>
                    <td className="px-3 py-2 text-slate-600">{b.author}</td>
                    <td className="px-3 py-2 text-slate-500">{b.isbn || "—"}</td>
                    <td className={`px-3 py-2 ${b.availableCopies === 0 ? "text-red-500" : ""}`}>
                      {b.availableCopies}/{b.totalCopies}
                    </td>
                    <td className="px-3 py-2">
                      <BorrowCell
                        book={b}
                        members={memberList}
                        busy={busyBorrowId === b.id}
                        onBorrow={(mid) => borrow(b, mid)}
                      />
                    </td>
                    <td className="px-3 py-2 text-right">
                      <button
                        onClick={() => { setEditingId(b.id); setCreateOpen(false); }}
                        className="rounded px-2 py-0.5 text-xs border border-slate-300 hover:bg-slate-100"
                      >
                        Edit
                      </button>
                    </td>
                  </tr>
                ),
              )}
            </tbody>
          </table>
        )}
        {!loading && (items.length > 0 || pagination.page > 1) && (
          <div className="border-t border-slate-100">
            <ServerPaginator
              page={pagination.page}
              pageSize={pagination.pageSize}
              hasMore={hasMore}
              onChange={handlePaginationChange}
            />
          </div>
        )}
      </div>
    </div>
  );
}

// ─── types ────────────────────────────────────────────────────────────────────

interface BookFormValues {
  title: string;
  author: string;
  isbn: string;
  totalCopies: number;
}

// ─── inline edit row ──────────────────────────────────────────────────────────

function BookEditRow({
  book,
  onSaved,
  onCancel,
}: {
  book: Book;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<BookFormValues>({
    defaultValues: {
      title: book.title,
      author: book.author,
      isbn: book.isbn,
      totalCopies: book.totalCopies,
    },
  });

  const onSave = handleSubmit(async ({ title, author, isbn, totalCopies }) => {
    setServerError(null);
    try {
      await books.UpdateBook(
        { id: book.id, title: title.trim(), author: author.trim(), isbn: isbn.trim(), totalCopies },
        authMetadata(),
      );
      onSaved();
    } catch (err) {
      setServerError(rpcMessage(err, "update failed"));
    }
  });

  function onKey(e: React.KeyboardEvent) {
    if (e.key === "Enter") { e.preventDefault(); onSave(); }
    if (e.key === "Escape") onCancel();
  }

  return (
    <>
      <tr className="border-t border-slate-100 bg-slate-50">
        <td className="px-2 py-1.5">
          <InlineInput
            {...register("title", { validate: (v) => requireText(v, "Title") ?? true })}
            error={errors.title?.message}
            placeholder="Title"
            onKeyDown={onKey}
          />
        </td>
        <td className="px-2 py-1.5">
          <InlineInput
            {...register("author", { validate: (v) => requireText(v, "Author") ?? true })}
            error={errors.author?.message}
            placeholder="Author"
            onKeyDown={onKey}
          />
        </td>
        <td className="px-2 py-1.5">
          <InlineInput {...register("isbn")} placeholder="ISBN" onKeyDown={onKey} />
        </td>
        <td className="px-2 py-1.5">
          <InlineInput
            {...register("totalCopies", {
              valueAsNumber: true,
              validate: (v) => requireMin(v, 1, "Copies") ?? true,
            })}
            type="number"
            error={errors.totalCopies?.message}
            onKeyDown={onKey}
          />
        </td>
        <td className="px-2 py-1.5 text-slate-400 text-xs italic">—</td>
        <td className="px-2 py-1.5">
          <div className="flex items-center gap-1.5 justify-end">
            <button
              onClick={onSave}
              disabled={isSubmitting}
              className="rounded bg-slate-900 px-2.5 py-1 text-xs text-white hover:bg-slate-800 disabled:opacity-50"
            >
              {isSubmitting ? "…" : "Save"}
            </button>
            <button
              onClick={onCancel}
              className="rounded border border-slate-300 px-2.5 py-1 text-xs hover:bg-slate-100"
            >
              Cancel
            </button>
          </div>
        </td>
      </tr>
      {serverError && (
        <tr className="bg-red-50">
          <td colSpan={6} className="px-3 py-1.5 text-xs text-red-600">{serverError}</td>
        </tr>
      )}
    </>
  );
}

// ─── create form ──────────────────────────────────────────────────────────────

function BookCreateForm({ onDone, onCancel }: { onDone: () => void; onCancel: () => void }) {
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<BookFormValues>({ defaultValues: { title: "", author: "", isbn: "", totalCopies: 1 } });

  const onSubmit = handleSubmit(async ({ title, author, isbn, totalCopies }) => {
    setServerError(null);
    try {
      await books.CreateBook(
        { title: title.trim(), author: author.trim(), isbn: isbn.trim(), totalCopies },
        authMetadata(),
      );
      reset();
      onDone();
    } catch (err) {
      setServerError(rpcMessage(err, "failed"));
    }
  });

  return (
    <form
      onSubmit={onSubmit}
      className="grid grid-cols-1 gap-3 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-4"
    >
      <div className="flex flex-col gap-1">
        <input
          {...register("title", { validate: (v) => requireText(v, "Title") ?? true })}
          placeholder="Title *"
          className={inputCls(!!errors.title)}
        />
        {errors.title && <FieldError msg={errors.title.message!} />}
      </div>
      <div className="flex flex-col gap-1">
        <input
          {...register("author", { validate: (v) => requireText(v, "Author") ?? true })}
          placeholder="Author *"
          className={inputCls(!!errors.author)}
        />
        {errors.author && <FieldError msg={errors.author.message!} />}
      </div>
      <input {...register("isbn")} placeholder="ISBN (optional)" className={inputCls(false)} />
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <input
            {...register("totalCopies", {
              valueAsNumber: true,
              validate: (v) => requireMin(v, 1, "Copies") ?? true,
            })}
            type="number"
            min={1}
            className={inputCls(!!errors.totalCopies) + " w-20"}
          />
          <button
            type="submit"
            disabled={isSubmitting}
            className="rounded-md bg-slate-900 px-3 py-2 text-sm text-white hover:bg-slate-800 disabled:opacity-50"
          >
            {isSubmitting ? "Saving…" : "Save"}
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm hover:bg-slate-100"
          >
            Cancel
          </button>
        </div>
        {errors.totalCopies && <FieldError msg={errors.totalCopies.message!} />}
      </div>
      {serverError && (
        <p className="sm:col-span-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {serverError}
        </p>
      )}
    </form>
  );
}

// ─── BorrowCell ───────────────────────────────────────────────────────────────

function BorrowCell({
  book,
  members,
  busy,
  onBorrow,
}: {
  book: Book;
  members: Member[];
  busy: boolean;
  onBorrow: (memberId: number) => void;
}) {
  const [memberId, setMemberId] = useState<number>(members[0]?.id ?? 0);
  useEffect(() => {
    if (!memberId && members.length > 0) setMemberId(members[0].id);
  }, [members, memberId]);

  const canBorrow = book.availableCopies > 0 && memberId > 0 && !busy;
  return (
    <div className="flex items-center gap-2">
      <select
        value={memberId}
        onChange={(e) => setMemberId(Number(e.target.value))}
        className="rounded-md border border-slate-300 px-2 py-1 text-sm"
      >
        {members.length === 0 && <option value={0}>No members</option>}
        {members.map((m) => (
          <option key={m.id} value={m.id}>{m.fullName}</option>
        ))}
      </select>
      <button
        disabled={!canBorrow}
        onClick={() => onBorrow(memberId)}
        className="rounded-md bg-slate-900 px-3 py-1 text-sm text-white hover:bg-slate-800 disabled:opacity-50"
      >
        {busy ? "…" : "Borrow"}
      </button>
    </div>
  );
}

// ─── shared UI helpers ────────────────────────────────────────────────────────

const InlineInput = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement> & { error?: string }
>(({ error, className: _cls, ...props }, ref) => (
  <div className="flex flex-col gap-0.5">
    <input
      ref={ref}
      {...props}
      className={[
        "rounded border px-2 py-1 text-sm w-full",
        error ? "border-red-400 bg-red-50" : "border-slate-300 bg-white",
      ].join(" ")}
    />
    {error && <span className="text-xs text-red-600">{error}</span>}
  </div>
));
InlineInput.displayName = "InlineInput";

function inputCls(hasError: boolean) {
  return [
    "rounded-md border px-3 py-2 text-sm w-full",
    hasError ? "border-red-400 bg-red-50" : "border-slate-300",
  ].join(" ");
}

function FieldError({ msg }: { msg: string }) {
  return <span className="text-xs text-red-600">{msg}</span>;
}

function RowSkeleton({ cols }: { cols: number }) {
  return (
    <div className="divide-y divide-slate-100">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex gap-4 px-3 py-3">
          {Array.from({ length: cols }).map((_, j) => (
            <div key={j} className="h-4 flex-1 animate-pulse rounded bg-slate-100" />
          ))}
        </div>
      ))}
    </div>
  );
}
