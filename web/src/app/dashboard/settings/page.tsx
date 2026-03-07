"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useGrove } from "@/hooks/useGrove";
import { createClient } from "@/lib/supabase/client";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { User, Camera, Bell, Moon, LogOut } from "lucide-react";

export default function SettingsPage() {
  const { user, displayName, signOut } = useAuth();
  const { grove } = useGrove();
  const [name, setName] = useState(displayName);
  const [saving, setSaving] = useState(false);
  const [darkMode, setDarkMode] = useState(true);
  const supabase = createClient();

  useEffect(() => {
    setName(displayName);
  }, [displayName]);

  useEffect(() => {
    const isDark = document.documentElement.classList.contains("dark");
    setDarkMode(isDark);
  }, []);

  async function handleSaveName() {
    if (!user || !name.trim()) return;
    setSaving(true);

    const { error } = await supabase.auth.updateUser({
      data: { display_name: name.trim() },
    });

    if (!error) {
      await supabase.from("users").update({ display_name: name.trim() }).eq("id", user.id);
      toast.success("Display name updated");
    } else {
      toast.error(error.message);
    }
    setSaving(false);
  }

  function toggleDarkMode() {
    const html = document.documentElement;
    if (darkMode) {
      html.classList.remove("dark");
    } else {
      html.classList.add("dark");
    }
    setDarkMode(!darkMode);
  }

  return (
    <div className="p-4 md:p-6 max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground">Manage your account and preferences</p>
      </div>

      {/* Profile */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <User className="h-4 w-4" /> Profile
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Email</label>
            <Input value={user?.email || ""} disabled />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Display Name</label>
            <div className="flex gap-2">
              <Input value={name} onChange={(e) => setName(e.target.value)} />
              <Button onClick={handleSaveName} disabled={saving || name === displayName}>
                {saving ? "Saving..." : "Save"}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Grove */}
      {grove && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Grove</CardTitle>
            <CardDescription>You are in {grove.name}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Invite code:</span>
              <Badge variant="secondary" className="text-sm tracking-wider">
                {grove.invite_code}
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Daily goal:</span>
              <span className="text-sm font-medium">{grove.daily_goal_hours}h</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Preferences */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Preferences</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Camera className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm">Camera permissions</span>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                navigator.mediaDevices
                  .getUserMedia({ video: true })
                  .then((s) => {
                    s.getTracks().forEach((t) => t.stop());
                    toast.success("Camera access granted");
                  })
                  .catch(() => toast.error("Camera access denied"));
              }}
            >
              Test
            </Button>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Moon className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm">Dark mode</span>
            </div>
            <Button variant="outline" size="sm" onClick={toggleDarkMode}>
              {darkMode ? "On" : "Off"}
            </Button>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bell className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm">Notifications</span>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                if ("Notification" in window) {
                  Notification.requestPermission().then((p) => {
                    toast.success(`Notifications: ${p}`);
                  });
                }
              }}
            >
              Enable
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Sign out */}
      <Card>
        <CardContent className="pt-6">
          <Button variant="destructive" className="w-full" onClick={signOut}>
            <LogOut className="h-4 w-4 mr-2" /> Sign Out
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
