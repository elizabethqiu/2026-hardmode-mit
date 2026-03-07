"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function GroveDetailPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/dashboard/grove");
  }, [router]);

  return null;
}
