// What a signed-in marketplace browser keeps (D082): the refresh token and who it is. Pure logic only.
// The access token lives in memory only, as in the farmer app.

export type MarketRole = "customer" | "operator" | "admin" | "farmer";

export interface MarketUser {
  id: number;
  name: string;
  phone: string;
  role: MarketRole;
}

export interface StoredUser {
  refreshToken: string;
  user: MarketUser;
}

const VERSION = 1;
const ROLES: readonly MarketRole[] = ["customer", "operator", "admin", "farmer"];

export function toStoredUser(stored: StoredUser): string {
  return JSON.stringify({ version: VERSION, ...stored });
}

export function fromStoredUser(text: string | null): StoredUser | null {
  try {
    const value = JSON.parse(text ?? "null") as { version?: unknown; refreshToken?: unknown; user?: Partial<MarketUser> } | null;
    if (value?.version !== VERSION || typeof value.refreshToken !== "string") return null;
    const user = value.user;
    if (
      typeof user?.id !== "number" ||
      typeof user.name !== "string" ||
      typeof user.phone !== "string" ||
      !ROLES.includes(user.role as MarketRole)
    ) {
      return null;
    }
    return { refreshToken: value.refreshToken, user: { id: user.id, name: user.name, phone: user.phone, role: user.role as MarketRole } };
  } catch {
    return null;
  }
}

/** Operators and admins run the warehouse; customers shop; a farmer sells from the farmer app. */
export function canRunWarehouse(role: MarketRole | null): boolean {
  return role === "operator" || role === "admin";
}

export function canShop(role: MarketRole | null): boolean {
  return role === "customer";
}
