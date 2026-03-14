import { AppSession } from "@mentra/sdk";

class UserSession {
  private appSession: AppSession | null = null;

  setAppSession(session: AppSession) {
    this.appSession = session;
  }

  getAppSession(): AppSession | null {
    return this.appSession;
  }
}

class SessionManager {
  private userSessions = new Map<string, UserSession>();

  getOrCreate(userId: string): UserSession {
    const existing = this.userSessions.get(userId);
    if (existing) return existing;

    const created = new UserSession();
    this.userSessions.set(userId, created);
    return created;
  }

  get(userId: string): UserSession | undefined {
    return this.userSessions.get(userId);
  }

  remove(userId: string) {
    this.userSessions.delete(userId);
  }
}

export const sessions = new SessionManager();
