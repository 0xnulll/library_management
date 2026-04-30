"use client";

import { useEffect, useState } from "react";
import {
  authMetadata,
  books as booksClient,
  loans as loansClient,
  members as membersClient,
  rpcMessage,
} from "@/lib/grpc";
import { ServerPaginator, type PaginationState } from "@/components/DataTable";
import type { Book } from "@/lib/proto/book";
import type { Loan } from "@/lib/proto/loan";
import type { Member } from "@/lib/proto/member";

interface Row extends Loan {
  book?: Book;
  member?: Member;
}

export default function LoansPage() {
  const [rows, setRows] = useState<Row[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [activeOnly, setActiveOnly] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [pagination, setPagination] = useState<PaginationState>({ page: 1, pageSize: 10 });

  // Books + members are reference data used only for display labels.
  // Load them once (up to 200 each); they're small and don't paginate with loans.
  const [bookMap, setBookMap] = useState<Map<number, Book>>(new Map());
  const [memberMap, setMemberMap] = useState<Map<number, Member>>(new Map());

  async function loadRefs() {
    try {
      const meta = authMetadata();
      const [br, mr] = await Promise.all([
        booksClient.SearchBooks({ query: "", pagination: { limit: 200, offset: 0 } }, meta),
        membersClient.ListMembers({ pagination: { limit: 200, offset: 0 } }, meta),
      ]);
      setBookMap(new Map(br.books.map((b) => [b.id, b])));
      setMemberMap(new Map(mr.members.map((m) => [m.id, m])));
    } catch {
      // non-fatal — labels degrade to IDs
    }
  }

  async function load(pg: PaginationState, active: boolean) {
    setLoading(true);
    setError(null);
    try {
      const offset = (pg.page - 1) * pg.pageSize;
      const resp = await loansClient.ListLoans(
        { memberId: 0, bookId: 0, activeOnly: active, pagination: { limit: pg.pageSize, offset } },
        authMetadata(),
      );
      setRows(resp.loans as Row[]);
      setHasMore(resp.loans.length === pg.pageSize);
    } catch (err) {
      setError(rpcMessage(err, "failed to load"));
    } finally {
      setLoading(false);
    }
  }

  // Load reference data once on mount
  useEffect(() => { loadRefs(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Reload loans when page/size/filter changes
  useEffect(() => {
    load(pagination, activeOnly);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pagination, activeOnly]);

  async function returnLoan(id: number) {
    setBusyId(id);
    setError(null);
    try {
      await loansClient.ReturnLoan({ loanId: id }, authMetadata());
      await load(pagination, activeOnly);
    } catch (err) {
      setError(rpcMessage(err, "return failed"));
    } finally {
      setBusyId(null);
    }
  }

  function handlePaginationChange(p: PaginationState) {
    setPagination(p);
  }

  return (
    <div className="space-y-4">
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={activeOnly}
          onChange={(e) => {
            setActiveOnly(e.target.checked);
            setPagination((p) => ({ ...p, page: 1 }));
          }}
        />
        Active only
      </label>

      {error && <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        {loading ? (
          <RowSkeleton />
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-slate-600">
              <tr>
                <th className="px-3 py-2 font-medium">Book</th>
                <th className="px-3 py-2 font-medium">Member</th>
                <th className="px-3 py-2 font-medium">Borrowed</th>
                <th className="px-3 py-2 font-medium">Due</th>
                <th className="px-3 py-2 font-medium">Returned</th>
                <th className="px-3 py-2 font-medium">Action</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-3 py-8 text-center text-slate-400">
                    Nothing to show.
                  </td>
                </tr>
              )}
              {rows.map((r) => (
                <tr key={r.id} className="border-t border-slate-100 hover:bg-slate-50/50">
                  <td className="px-3 py-2 font-medium">
                    {bookMap.get(r.bookId)?.title ?? `#${r.bookId}`}
                  </td>
                  <td className="px-3 py-2 text-slate-600">
                    {memberMap.get(r.memberId)?.fullName ?? `#${r.memberId}`}
                  </td>
                  <td className="px-3 py-2 text-slate-500">{fmt(r.borrowedAt)}</td>
                  <td className={`px-3 py-2 ${r.isOverdue ? "text-red-600 font-medium" : "text-slate-500"}`}>
                    {fmt(r.dueAt)}{r.isOverdue && " (overdue)"}
                  </td>
                  <td className="px-3 py-2 text-slate-500">{fmt(r.returnedAt)}</td>
                  <td className="px-3 py-2">
                    {r.returnedAt ? (
                      <span className="text-slate-400 text-xs">returned</span>
                    ) : (
                      <button
                        disabled={busyId === r.id}
                        onClick={() => returnLoan(r.id)}
                        className="rounded-md bg-slate-900 px-3 py-1 text-xs text-white hover:bg-slate-800 disabled:opacity-50"
                      >
                        {busyId === r.id ? "…" : "Return"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {!loading && (rows.length > 0 || pagination.page > 1) && (
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

function fmt(d: Date | undefined): string {
  if (!d) return "—";
  return new Date(d).toLocaleString();
}

function RowSkeleton() {
  return (
    <div className="divide-y divide-slate-100">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex gap-4 px-3 py-3">
          {Array.from({ length: 6 }).map((_, j) => (
            <div key={j} className="h-4 flex-1 animate-pulse rounded bg-slate-100" />
          ))}
        </div>
      ))}
    </div>
  );
}
