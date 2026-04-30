"use client";

import React, { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { authMetadata, members as membersClient, rpcMessage } from "@/lib/grpc";
import { requireEmail, requireText } from "@/lib/validate";
import { ServerPaginator, type PaginationState } from "@/components/DataTable";
import type { Member } from "@/lib/proto/member";

// ─── page ─────────────────────────────────────────────────────────────────────

export default function MembersPage() {
  const [items, setItems] = useState<Member[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);

  const [createOpen, setCreateOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [pagination, setPagination] = useState<PaginationState>({ page: 1, pageSize: 10 });

  async function load(pg: PaginationState) {
    setLoading(true);
    setPageError(null);
    try {
      const offset = (pg.page - 1) * pg.pageSize;
      const resp = await membersClient.ListMembers(
        { pagination: { limit: pg.pageSize, offset } },
        authMetadata(),
      );
      setItems(resp.members);
      setHasMore(resp.members.length === pg.pageSize);
    } catch (e) {
      setPageError(rpcMessage(e, "failed to load"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(pagination);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pagination]);

  function handlePaginationChange(p: PaginationState) {
    setEditingId(null);
    setPagination(p);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-700">Members</h2>
        <button
          onClick={() => { setCreateOpen((v) => !v); setEditingId(null); }}
          className="rounded-md border border-slate-300 px-4 py-2 text-sm hover:bg-slate-100"
        >
          {createOpen ? "Close" : "Add member"}
        </button>
      </div>

      {createOpen && (
        <MemberCreateForm
          onDone={() => { setCreateOpen(false); load(pagination); }}
          onCancel={() => setCreateOpen(false)}
        />
      )}

      {pageError && (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{pageError}</p>
      )}

      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        {loading ? (
          <RowSkeleton cols={4} />
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-slate-600">
              <tr>
                <th className="px-3 py-2 font-medium">Name</th>
                <th className="px-3 py-2 font-medium">Email</th>
                <th className="px-3 py-2 font-medium">Phone</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              {items.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-3 py-8 text-center text-slate-400">
                    No members yet.
                  </td>
                </tr>
              )}
              {items.map((m) =>
                editingId === m.id ? (
                  <MemberEditRow
                    key={m.id}
                    member={m}
                    onSaved={() => { setEditingId(null); load(pagination); }}
                    onCancel={() => setEditingId(null)}
                  />
                ) : (
                  <tr key={m.id} className="border-t border-slate-100 hover:bg-slate-50/50">
                    <td className="px-3 py-2 font-medium">{m.fullName}</td>
                    <td className="px-3 py-2 text-slate-600">{m.email}</td>
                    <td className="px-3 py-2 text-slate-500">{m.phone || "—"}</td>
                    <td className="px-3 py-2 text-right">
                      <button
                        onClick={() => { setEditingId(m.id); setCreateOpen(false); }}
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

interface MemberFormValues {
  fullName: string;
  email: string;
  phone: string;
}

// ─── inline edit row ──────────────────────────────────────────────────────────

function MemberEditRow({
  member,
  onSaved,
  onCancel,
}: {
  member: Member;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<MemberFormValues>({
    defaultValues: { fullName: member.fullName, email: member.email, phone: member.phone },
  });

  const onSave = handleSubmit(async ({ fullName, email, phone }) => {
    setServerError(null);
    try {
      await membersClient.UpdateMember(
        { id: member.id, fullName: fullName.trim(), email: email.trim(), phone: phone.trim() },
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
            {...register("fullName", { validate: (v) => requireText(v, "Full name") ?? true })}
            error={errors.fullName?.message}
            placeholder="Full name"
            onKeyDown={onKey}
          />
        </td>
        <td className="px-2 py-1.5">
          <InlineInput
            {...register("email", { validate: (v) => requireEmail(v) ?? true })}
            error={errors.email?.message}
            placeholder="Email"
            onKeyDown={onKey}
          />
        </td>
        <td className="px-2 py-1.5">
          <InlineInput {...register("phone")} placeholder="Phone (optional)" onKeyDown={onKey} />
        </td>
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
          <td colSpan={4} className="px-3 py-1.5 text-xs text-red-600">{serverError}</td>
        </tr>
      )}
    </>
  );
}

// ─── create form ──────────────────────────────────────────────────────────────

function MemberCreateForm({ onDone, onCancel }: { onDone: () => void; onCancel: () => void }) {
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<MemberFormValues>({ defaultValues: { fullName: "", email: "", phone: "" } });

  const onSubmit = handleSubmit(async ({ fullName, email, phone }) => {
    setServerError(null);
    try {
      await membersClient.CreateMember(
        { fullName: fullName.trim(), email: email.trim(), phone: phone.trim() },
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
          {...register("fullName", { validate: (v) => requireText(v, "Full name") ?? true })}
          placeholder="Full name *"
          className={inputCls(!!errors.fullName)}
        />
        {errors.fullName && <FieldError msg={errors.fullName.message!} />}
      </div>
      <div className="flex flex-col gap-1">
        <input
          {...register("email", { validate: (v) => requireEmail(v) ?? true })}
          placeholder="Email *"
          className={inputCls(!!errors.email)}
        />
        {errors.email && <FieldError msg={errors.email.message!} />}
      </div>
      <input
        {...register("phone")}
        placeholder="Phone (optional)"
        className={inputCls(false)}
      />
      <div className="flex items-center gap-2">
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded-md bg-slate-900 px-3 py-2 text-sm text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {isSubmitting ? "Saving…" : "Add member"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm hover:bg-slate-100"
        >
          Cancel
        </button>
      </div>
      {serverError && (
        <p className="sm:col-span-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {serverError}
        </p>
      )}
    </form>
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
