"use client";

import { grpc } from "@improbable-eng/grpc-web";
import { BrowserHeaders } from "browser-headers";
import {
  AuthServiceClientImpl,
  GrpcWebImpl as AuthGrpc,
} from "./proto/auth";
import {
  BookServiceClientImpl,
  GrpcWebImpl as BookGrpc,
} from "./proto/book";
import {
  MemberServiceClientImpl,
  GrpcWebImpl as MemberGrpc,
} from "./proto/member";
import {
  LoanServiceClientImpl,
  GrpcWebImpl as LoanGrpc,
} from "./proto/loan";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export const TOKEN_KEY = "library.token";

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

/** Build authentication metadata from the latest token in localStorage. */
export function authMetadata(): grpc.Metadata {
  const meta = new BrowserHeaders();
  const token = getToken();
  if (token) meta.set("authorization", `Bearer ${token}`);
  return meta;
}

const empty = new BrowserHeaders();

export const auth = new AuthServiceClientImpl(new AuthGrpc(API_BASE, { metadata: empty }));
export const books = new BookServiceClientImpl(new BookGrpc(API_BASE, { metadata: empty }));
export const members = new MemberServiceClientImpl(new MemberGrpc(API_BASE, { metadata: empty }));
export const loans = new LoanServiceClientImpl(new LoanGrpc(API_BASE, { metadata: empty }));

export interface RpcError extends Error {
  code: number;
}

export function rpcMessage(err: unknown, fallback = "request failed"): string {
  if (err instanceof Error) return err.message || fallback;
  if (typeof err === "string") return err;
  return fallback;
}

export function isUnauthenticated(err: unknown): boolean {
  return (
    typeof err === "object" &&
    err !== null &&
    "code" in err &&
    (err as RpcError).code === grpc.Code.Unauthenticated
  );
}
