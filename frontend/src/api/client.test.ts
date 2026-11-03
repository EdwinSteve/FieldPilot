import { describe, expect, it } from "vitest";
import { ApiError, toApiError } from "./client";

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
