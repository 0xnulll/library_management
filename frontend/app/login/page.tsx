"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { useRouter } from "next/navigation";
import { auth, rpcMessage, setToken } from "@/lib/grpc";
import { requireText } from "@/lib/validate";

interface LoginFields {
  username: string;
  password: string;
}

export default function LoginPage() {
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFields>({ defaultValues: { username: "admin", password: "admin" } });

  const onSubmit = handleSubmit(async ({ username, password }) => {
    setServerError(null);
    try {
      const resp = await auth.Login({ username: username.trim(), password });
      setToken(resp.accessToken);
      router.replace("/dashboard");
    } catch (err) {
      setServerError(rpcMessage(err, "login failed"));
    }
  });

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm space-y-4 rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
      >
        <h1 className="text-xl font-semibold">Staff sign in</h1>
        <p className="text-sm text-slate-500">
          Default credentials are <code>admin</code> / <code>admin</code> in dev.
        </p>

        <label className="block">
          <span className="text-sm font-medium">Username</span>
          <input
            {...register("username", { validate: (v) => requireText(v, "Username") ?? true })}
            autoComplete="username"
            className={fieldCls(!!errors.username)}
          />
          {errors.username && <FieldError msg={errors.username.message!} />}
        </label>

        <label className="block">
          <span className="text-sm font-medium">Password</span>
          <input
            {...register("password", { validate: (v) => requireText(v, "Password") ?? true })}
            type="password"
            autoComplete="current-password"
            className={fieldCls(!!errors.password)}
          />
          {errors.password && <FieldError msg={errors.password.message!} />}
        </label>

        {serverError && (
          <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{serverError}</p>
        )}

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full rounded-md bg-slate-900 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-60"
        >
          {isSubmitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </main>
  );
}

function fieldCls(hasError: boolean) {
  return [
    "mt-1 w-full rounded-md border px-3 py-2 outline-none focus:border-slate-500",
    hasError ? "border-red-400 bg-red-50" : "border-slate-300",
  ].join(" ");
}

function FieldError({ msg }: { msg: string }) {
  return <span className="mt-0.5 block text-xs text-red-600">{msg}</span>;
}
