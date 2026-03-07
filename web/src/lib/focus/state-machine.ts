export type FocusState = "FOCUSED" | "IDLE" | "DOZING" | "AWAY";

interface StateTransition {
  time: number;
  state: FocusState;
}

export class FocusStateMachine {
  private currentState: FocusState = "AWAY";
  private stateStart = Date.now();
  private history: StateTransition[] = [];
  private nudgeFired = false;
  private awaySince: number | null = Date.now();

  constructor(
    private dozingThreshold = 90,
    private idleThreshold = 300,
    private focusedBreakThreshold = 25 * 60,
    private awaySleepThreshold = 10 * 60,
    private historyMaxLen = 20
  ) {}

  update(newState: FocusState): number {
    const now = Date.now() / 1000;

    if (newState === "AWAY") {
      if (this.currentState !== "AWAY") this.awaySince = now;
    } else {
      this.awaySince = null;
    }

    if (newState !== this.currentState) {
      this.history.push({ time: now, state: this.currentState });
      if (this.history.length > this.historyMaxLen) this.history.shift();
      this.currentState = newState;
      this.stateStart = now;
      this.nudgeFired = false;
    }

    return now - this.stateStart;
  }

  checkTriggers(duration: number, eyeAspectRatio = 1.0): "TRIGGER_CLAUDE" | "NONE" {
    if (this.nudgeFired) return "NONE";

    if (this.currentState === "AWAY" && duration >= this.awaySleepThreshold) {
      return "NONE";
    }

    let shouldTrigger = false;

    if (this.currentState === "DOZING" && duration >= this.dozingThreshold) {
      shouldTrigger = true;
    } else if (this.currentState === "IDLE" && duration >= this.idleThreshold) {
      shouldTrigger = true;
    } else if (this.currentState === "FOCUSED" && duration >= this.focusedBreakThreshold) {
      shouldTrigger = true;
    }

    if (shouldTrigger) {
      this.nudgeFired = true;
      return "TRIGGER_CLAUDE";
    }
    return "NONE";
  }

  recentHistory(n = 6): FocusState[] {
    const items = this.history.slice(-n).map((t) => t.state);
    items.push(this.currentState);
    return items.slice(-n);
  }

  get state() {
    return this.currentState;
  }

  get duration() {
    return Date.now() / 1000 - this.stateStart;
  }
}
