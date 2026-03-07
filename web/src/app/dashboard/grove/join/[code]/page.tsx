"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useGrove } from "@/hooks/useGrove";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export default function JoinGrovePage() {
  const params = useParams();
  const router = useRouter();
  const { grove, joinGrove, loading } = useGrove();
  const [joining, setJoining] = useState(false);
  const code = params.code as string;

  useEffect(() => {
    if (grove) {
      toast.info("You are already in a grove");
      router.push("/dashboard/grove");
    }
  }, [grove, router]);

  async function handleJoin() {
    setJoining(true);
    const result = await joinGrove(code);
    setJoining(false);
    if (result) {
      toast.success(`Joined ${result.name}!`);
      router.push("/dashboard/grove");
    } else {
      toast.error("Invalid or expired invite code");
    }
  }

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[50vh]">
        <div className="animate-pulse text-muted-foreground">Loading...</div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-md mx-auto">
      <Card>
        <CardHeader className="text-center">
          <div className="text-4xl mb-2">🍄</div>
          <CardTitle>Join Grove</CardTitle>
          <CardDescription>
            You&apos;ve been invited to join a study grove with code{" "}
            <span className="font-mono font-bold">{code}</span>
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button className="w-full" onClick={handleJoin} disabled={joining}>
            {joining ? "Joining..." : "Accept Invitation"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
