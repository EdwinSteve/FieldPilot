const API_BASE = "/api";

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

async function request<T>(
  method: string,
  path: string,
  body?: BodyInit,
  headers?: Record<string, string>,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { method, body, headers });
  if (!response.ok) {
    throw await toApiError(response, `${method} ${path}`);
  }
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
