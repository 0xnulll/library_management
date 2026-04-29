"use client";

import { useEffect, useState } from "react";
import { authMetadata, books, loans, members, rpcMessage } from "@/lib/grpc";
import type { Book } from "@/lib/proto/book";
import type { Member } from "@/lib/proto/member";

export default function BooksPage() {
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<Book[]>([]);
  const [memberList, setMemberList] = useState<Member[]>([]);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  async function load() {
    setError(null);
    try {
      const meta = authMetadata();
      const [b, m] = await Promise.all([
        books.SearchBooks(
          { query: query.trim(), pagination: { limit: 200, offset: 0 } },
          meta,
        ),
        members.ListMembers({ pagination: { limit: 200, offset: 0 } }, meta),
      ]);
      setItems(b.books);
      setMemberList(m.members);
    } catch (err) {
      setError(rpcMessage(err, "failed to load"));
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function borrow(book: Book, memberId: number) {
    if (!memberId) return;
    setBusyId(book.id);
    setError(null);
    setMessage(null);
    try {
      await loans.Borrow({ bookId: book.id, memberId, days: 0 }, authMetadata());
      setMessage(`Lent "${book.title}".`);
      await load();
    } catch (err) {
      setError(rpcMessage(err, "borrow failed"));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") load();
          }}
          placeholder="Search by title, author, or ISBN..."
          className="flex-1 rounded-md border border-slate-300 px-3 py-2"
        />
        <button
          onClick={load}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
        >
          Search
        </button>
        <button
          onClick={() => setCreateOpen((v) => !v)}
          className="rounded-md border border-slate-300 px-4 py-2 text-sm hover:bg-slate-100"
        >
          {createOpen ? "Close" : "Add book"}
        </button>
      </div>

      {createOpen && <CreateBook onCreated={load} />}

      {message && (
        <p className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{message}</p>
      )}
      {error && <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-slate-600">
            <tr>
              <th className="px-3 py-2">Title</th>
              <th className="px-3 py-2">Author</th>
              <th className="px-3 py-2">ISBN</th>
              <th className="px-3 py-2">Available</th>
              <th className="px-3 py-2">Borrow</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-slate-500">
                  No books found.
                </td>
              </tr>
            )}
            {items.map((b) => (
              <BookRow
                key={b.id}
                book={b}
                members={memberList}
                busy={busyId === b.id}
                onBorrow={(mid) => borrow(b, mid)}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function BookRow({
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
    <tr className="border-t border-slate-100">
      <td className="px-3 py-2 font-medium">{book.title}</td>
      <td className="px-3 py-2 text-slate-600">{book.author}</td>
      <td className="px-3 py-2 text-slate-500">{book.isbn || "—"}</td>
      <td className="px-3 py-2">
        {book.availableCopies}/{book.totalCopies}
      </td>
      <td className="px-3 py-2">
        <div className="flex items-center gap-2">
          <select
            value={memberId}
            onChange={(e) => setMemberId(Number(e.target.value))}
            className="rounded-md border border-slate-300 px-2 py-1 text-sm"
          >
            {members.length === 0 && <option value={0}>No members</option>}
            {members.map((m) => (
              <option key={m.id} value={m.id}>
                {m.fullName}
              </option>
            ))}
          </select>
          <button
            disabled={!canBorrow}
            onClick={() => onBorrow(memberId)}
            className="rounded-md bg-slate-900 px-3 py-1 text-sm text-white hover:bg-slate-800 disabled:opacity-50"
          >
            {busy ? "..." : "Borrow"}
          </button>
        </div>
      </td>
    </tr>
  );
}

function CreateBook({ onCreated }: { onCreated: () => void }) {
  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");
  const [isbn, setIsbn] = useState("");
  const [copies, setCopies] = useState(1);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      await books.CreateBook(
        { title, author, isbn, totalCopies: copies },
        authMetadata(),
      );
      setTitle("");
      setAuthor("");
      setIsbn("");
      setCopies(1);
      onCreated();
    } catch (e) {
      setErr(rpcMessage(e, "failed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      onSubmit={submit}
      className="grid grid-cols-1 gap-3 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-4"
    >
      <input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Title"
        required
        className="rounded-md border border-slate-300 px-3 py-2 text-sm"
      />
      <input
        value={author}
        onChange={(e) => setAuthor(e.target.value)}
        placeholder="Author"
        required
        className="rounded-md border border-slate-300 px-3 py-2 text-sm"
      />
      <input
        value={isbn}
        onChange={(e) => setIsbn(e.target.value)}
        placeholder="ISBN (optional)"
        className="rounded-md border border-slate-300 px-3 py-2 text-sm"
      />
      <div className="flex items-center gap-2">
        <input
          type="number"
          min={0}
          value={copies}
          onChange={(e) => setCopies(Number(e.target.value))}
          className="w-20 rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={busy}
          className="ml-auto rounded-md bg-slate-900 px-3 py-2 text-sm text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {busy ? "Saving..." : "Save"}
        </button>
      </div>
      {err && (
        <p className="sm:col-span-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{err}</p>
      )}
    </form>
  );
}
