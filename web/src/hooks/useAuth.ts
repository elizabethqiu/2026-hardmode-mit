"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import type { User } from "@supabase/supabase-js";

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const supabase = createClient();

  useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => {
      setUser(user);
      setDisplayName(user?.user_metadata?.display_name ?? user?.email?.split("@")[0] ?? "");
      setLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      setDisplayName(session?.user?.user_metadata?.display_name ?? "");
    });

    return () => subscription.unsubscribe();
  }, []);

  async function signOut() {
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  }

  return { user, displayName, loading, signOut };
}
