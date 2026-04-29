"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { TOKEN_KEY } from "@/lib/grpc";

export default function Index() {
  const router = useRouter();
  useEffect(() => {
    const token = window.localStorage.getItem(TOKEN_KEY);
    router.replace(token ? "/dashboard" : "/login");
  }, [router]);
  return null;
}
