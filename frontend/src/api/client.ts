const API_BASE = "/api";

/** The dashboard URL of a backend path (for resources an <img> loads itself). */
export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

/** The backend's error body (§7): an error class name and a safe message. */
interface ErrorBody {
  error?: string;
  message?: string;
  detail?: unknown;
}

/** Error raised when the backend answers with a non-2xx status. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** GET a JSON resource from the backend. */
export function getJson<T>(path: string): Promise<T> {
  return request<T>("GET", path);
}

/** POST a JSON body (or nothing) and read the JSON answer. */
export function postJson<T>(path: string, body?: unknown): Promise<T> {
  return request<T>("POST", path, body === undefined ? undefined : JSON.stringify(body), {
    "Content-Type": "application/json",
  });
}

/** POST raw bytes, such as a WAV recording (D066). */
export function postBytes<T>(path: string, body: Blob, contentType: string): Promise<T> {
  return request<T>("POST", path, body, { "Content-Type": contentType });
}

/** How an app that logs in joins its session to every call (D082). */
export interface Session {
  /** The Authorization header to send, or none when signed out. */
  headers: () => Record<string, string>;
  /** Renews an expired session after a 401; true when the call should be sent again. */
  renew: () => Promise<boolean>;
}

let session: Session | null = null;

/** Set once by an app that logs in; without it, calls go out as before. */
export function setSession(next: Session | null): void {
  session = next;
}

async function request<T>(
  method: string,
  path: string,
  body?: BodyInit,
  headers?: Record<string, string>,
): Promise<T> {
  const send = () =>
    fetch(apiUrl(path), { method, body, headers: { ...headers, ...session?.headers() } });
  let response = await send();
  if (response.status === 401 && session !== null && (await session.renew())) {
    response = await send();
  }
  if (!response.ok) {
    throw await toApiError(response, `${method} ${path}`);
  }
  // 204 No Content, as a logout answers.
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/** The backend's own message when it sent one; never a stack trace. */
export async function toApiError(response: Response, what: string): Promise<ApiError> {
  let body: ErrorBody = {};
  try {
    body = (await response.json()) as ErrorBody;
  } catch {
    // Not JSON (a proxy error page, for example): fall back to the status.
  }
  const message =
    typeof body.message === "string" ? body.message : `${what} falló (HTTP ${response.status})`;
  return new ApiError(response.status, body.error ?? "HttpError", message);
}
