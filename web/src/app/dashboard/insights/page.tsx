"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { BarChart3, TrendingUp, Lightbulb, Flame, Calendar } from "lucide-react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";

interface DaySummary {
  date: string;
  focus_hours: number;
}

interface Insight {
  text: string;
}

export default function InsightsPage() {
  const [focusHistory, setFocusHistory] = useState<DaySummary[]>([]);
  const [insights, setInsights] = useState<string[]>([]);
  const [summary, setSummary] = useState("");
  const [streak, setStreak] = useState(0);
  const [loading, setLoading] = useState(true);
  const supabase = createClient();

  useEffect(() => {
    loadInsights();
  }, []);

  async function loadInsights() {
    setLoading(true);
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) { setLoading(false); return; }

    // Load recent focus_history aggregated by day
    const { data: history } = await supabase
      .from("focus_history")
      .select("created_at, focus_score")
      .eq("user_id", user.id)
      .order("created_at", { ascending: true })
      .limit(500);

    if (history && history.length > 0) {
      const dailyMap = new Map<string, number>();
      for (const row of history) {
        const date = new Date(row.created_at).toISOString().split("T")[0];
        dailyMap.set(date, (dailyMap.get(date) || 0) + (row.focus_score > 0.5 ? 0.01 : 0));
      }

      const days = Array.from(dailyMap.entries())
        .map(([date, hours]) => ({ date, focus_hours: Math.round(hours * 10) / 10 }))
        .slice(-14);

      setFocusHistory(days);

      // Calculate streak
      let s = 0;
      const sorted = [...days].reverse();
      for (const d of sorted) {
        if (d.focus_hours > 0) s++;
        else break;
      }
      setStreak(s);
    }

    // Load daily summary from daily_summaries
    const today = new Date().toISOString().split("T")[0];
    const { data: summaryData } = await supabase
      .from("daily_summaries")
      .select("digest")
      .gte("summary_date", today)
      .limit(1)
      .single();

    if (summaryData?.digest) {
      try {
        const parsed = JSON.parse(summaryData.digest);
        if (parsed.insights) setInsights(parsed.insights);
        if (parsed.summary) setSummary(parsed.summary);
      } catch {
        setSummary(summaryData.digest);
      }
    }

    setLoading(false);
  }

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[50vh]">
        <div className="animate-pulse text-muted-foreground">Loading insights...</div>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Insights</h1>
        <p className="text-muted-foreground">Your focus patterns and progress over time</p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6 text-center">
            <Flame className="h-6 w-6 mx-auto mb-2 text-orange-400" />
            <p className="text-2xl font-bold">{streak}</p>
            <p className="text-xs text-muted-foreground">Day streak</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <TrendingUp className="h-6 w-6 mx-auto mb-2 text-green-400" />
            <p className="text-2xl font-bold">
              {focusHistory.length > 0
                ? Math.round(focusHistory.reduce((a, d) => a + d.focus_hours, 0) / focusHistory.length * 10) / 10
                : 0}h
            </p>
            <p className="text-xs text-muted-foreground">Avg daily focus</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <Calendar className="h-6 w-6 mx-auto mb-2 text-blue-400" />
            <p className="text-2xl font-bold">{focusHistory.length}</p>
            <p className="text-xs text-muted-foreground">Days tracked</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <BarChart3 className="h-6 w-6 mx-auto mb-2 text-purple-400" />
            <p className="text-2xl font-bold">
              {focusHistory.length > 0 ? Math.max(...focusHistory.map((d) => d.focus_hours)) : 0}h
            </p>
            <p className="text-xs text-muted-foreground">Best day</p>
          </CardContent>
        </Card>
      </div>

      {/* Focus chart */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Focus Hours (14 days)</CardTitle>
        </CardHeader>
        <CardContent>
          {focusHistory.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={focusHistory}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis
                  dataKey="date"
                  tickFormatter={(d: string) => d.slice(5)}
                  className="text-xs"
                />
                <YAxis className="text-xs" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "8px",
                    color: "hsl(var(--foreground))",
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="focus_hours"
                  stroke="hsl(var(--primary))"
                  fill="hsl(var(--primary))"
                  fillOpacity={0.2}
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-12">
              Start focus sessions to see your progress here
            </p>
          )}
        </CardContent>
      </Card>

      {/* AI Insights */}
      {(insights.length > 0 || summary) && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Lightbulb className="h-4 w-4" /> AI Insights
            </CardTitle>
            {summary && <CardDescription>{summary}</CardDescription>}
          </CardHeader>
          <CardContent>
            <ul className="space-y-3">
              {insights.map((insight, i) => (
                <li key={i} className="flex items-start gap-3 text-sm">
                  <Badge variant="secondary" className="mt-0.5 shrink-0">{i + 1}</Badge>
                  <span>{insight}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
