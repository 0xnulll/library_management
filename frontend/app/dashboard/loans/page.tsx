"use client";

import { useEffect, useState } from "react";
import {
  authMetadata,
  books as booksClient,
  loans as loansClient,
  members as membersClient,
  rpcMessage,
} from "@/lib/grpc";
import type { Book } from "@/lib/proto/book";
import type { Loan } from "@/lib/proto/loan";
import type { Member } from "@/lib/proto/member";

interface Row extends Loan {
  book?: Book;
  member?: Member;
}

export default function LoansPage() {
  const [rows, setRows] = useState<Row[]>([]);
  const [activeOnly, setActiveOnly] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setError(null);
    try {
      const meta = authMetadata();
      const [loanResp, bookResp, memberResp] = await Promise.all([
        loansClient.ListLoans(
          {
            memberId: 0,
            bookId: 0,
            activeOnly,
            pagination: { limit: 200, offset: 0 },
          },
          meta,
        ),
        booksClient.SearchBooks(
          { query: "", pagination: { limit: 200, offset: 0 } },
          meta,
        ),
        membersClient.ListMembers(
          { pagination: { limit: 200, offset: 0 } },
          meta,
        ),
      ]);
      const bookById = new Map(bookResp.books.map((b) => [b.id, b]));
      const memberById = new Map(memberResp.members.map((m) => [m.id, m]));
      setRows(
        loanResp.loans.map((l) => ({
          ...l,
          book: bookById.get(l.bookId),
          member: memberById.get(l.memberId),
        })),
      );
    } catch (err) {
      setError(rpcMessage(err, "failed to load"));
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOnly]);

  async function returnLoan(id: number) {
    setBusyId(id);
    setError(null);
    try {
      await loansClient.ReturnLoan({ loanId: id }, authMetadata());
      await load();
    } catch (err) {
      setError(rpcMessage(err, "return failed"));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="space-y-4">
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={activeOnly}
          onChange={(e) => setActiveOnly(e.target.checked)}
        />
        Active only
      </label>

      {error && <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-slate-600">
            <tr>
              <th className="px-3 py-2">Book</th>
              <th className="px-3 py-2">Member</th>
              <th className="px-3 py-2">Borrowed</th>
              <th className="px-3 py-2">Due</th>
              <th className="px-3 py-2">Returned</th>
              <th className="px-3 py-2">Action</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-slate-500">
                  Nothing to show.
                </td>
              </tr>
            )}
            {rows.map((r) => (
              <tr key={r.id} className="border-t border-slate-100">
                <td className="px-3 py-2 font-medium">{r.book?.title ?? `#${r.bookId}`}</td>
                <td className="px-3 py-2 text-slate-600">
                  {r.member?.fullName ?? `#${r.memberId}`}
                </td>
                <td className="px-3 py-2 text-slate-500">{fmt(r.borrowedAt)}</td>
                <td className={`px-3 py-2 ${r.isOverdue ? "text-red-600" : "text-slate-500"}`}>
                  {fmt(r.dueAt)} {r.isOverdue && "(overdue)"}
                </td>
                <td className="px-3 py-2 text-slate-500">{fmt(r.returnedAt)}</td>
                <td className="px-3 py-2">
                  {r.returnedAt ? (
                    <span className="text-slate-400">returned</span>
                  ) : (
                    <button
                      disabled={busyId === r.id}
                      onClick={() => returnLoan(r.id)}
                      className="rounded-md bg-slate-900 px-3 py-1 text-xs text-white hover:bg-slate-800 disabled:opacity-50"
                    >
                      {busyId === r.id ? "..." : "Return"}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function fmt(d: Date | undefined): string {
  if (!d) return "—";
  return new Date(d).toLocaleString();
}
