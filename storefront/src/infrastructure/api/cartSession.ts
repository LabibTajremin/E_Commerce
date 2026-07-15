const CART_SESSION_KEY = "cart_session_id";

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

export const cartSession = {
  getOrCreate(): string | null {
    if (!isBrowser()) return null;
    let sessionId = window.localStorage.getItem(CART_SESSION_KEY);
    if (!sessionId) {
      sessionId = crypto.randomUUID();
      window.localStorage.setItem(CART_SESSION_KEY, sessionId);
    }
    return sessionId;
  },
  clear(): void {
    if (!isBrowser()) return;
    window.localStorage.removeItem(CART_SESSION_KEY);
  },
};
