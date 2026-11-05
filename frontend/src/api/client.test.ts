import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, getJson, postJson, setSession, toApiError } from "./client";

function response(status: number, body: string, contentType = "application/json"): Response {
  return new Response(body, { status, headers: { "Content-Type": contentType } });
}

describe("toApiError", () => {
  it("keeps the backend's code and Spanish message", async () => {
    const body = JSON.stringify({
      error: "ChatUnavailableError",
      message: "El chat necesita MOCK_LLM=0 y una clave de API.",
    });

    const error = await toApiError(response(503, body), "POST /agent/chat");

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(503);
    expect(error.code).toBe("ChatUnavailableError");
    expect(error.message).toBe("El chat necesita MOCK_LLM=0 y una clave de API.");
  });

  it("falls back to the status when the body is not JSON", async () => {
    const error = await toApiError(response(502, "<html>Bad gateway</html>", "text/html"), "GET /plots");

    expect(error.code).toBe("HttpError");
    expect(error.message).toBe("GET /plots failed (HTTP 502)");
  });

  it("ignores a validation detail without a message", async () => {
    const body = JSON.stringify({ detail: [{ loc: ["body", "question"] }] });

    const error = await toApiError(response(422, body), "POST /agent/chat");

    expect(error.message).toBe("POST /agent/chat failed (HTTP 422)");
  });
});

describe("a session", () => {
  afterEach(() => {
    setSession(null);
    vi.unstubAllGlobals();
  });

  it("sends its header, renews once on a 401 and sends the call again", async () => {
    const calls: (string | undefined)[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>((_url, init) => {
        const headers = (init?.headers ?? {}) as Record<string, string>;
        const auth = headers.Authorization;
        calls.push(auth);
        const ok = auth === "Bearer new";
        return Promise.resolve(response(ok ? 200 : 401, ok ? "[]" : "{}"));
      }),
    );
    let token = "old";
    setSession({
      headers: () => ({ Authorization: `Bearer ${token}` }),
      renew: () => {
        token = "new";
        return Promise.resolve(true);
      },
    });

    await expect(getJson("/plots")).resolves.toEqual([]);
    expect(calls).toEqual(["Bearer old", "Bearer new"]);
  });

  it("gives up when the session cannot be renewed", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(() => Promise.resolve(response(401, "{}"))),
    );
    setSession({ headers: () => ({}), renew: () => Promise.resolve(false) });

    await expect(getJson("/plots")).rejects.toMatchObject({ status: 401 });
  });

  it("reads a 204 as no content", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(() => Promise.resolve(new Response(null, { status: 204 }))),
    );

    await expect(postJson("/auth/logout", {})).resolves.toBeUndefined();
  });
});
