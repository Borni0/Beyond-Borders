import { describe, expect, it } from "vitest";

import { copySetCookieHeaders } from "@/lib/cookies";

describe("copySetCookieHeaders", () => {
  it("preserves all Set-Cookie values from the upstream response", () => {
    const upstream = new Headers();
    upstream.append("set-cookie", "bb_session=abc123; Path=/; HttpOnly; SameSite=Lax");
    upstream.append("set-cookie", "theme=dark; Path=/");

    const forwarded = new Headers();
    copySetCookieHeaders(upstream, forwarded);

    expect(forwarded.getSetCookie()).toEqual([
      "bb_session=abc123; Path=/; HttpOnly; SameSite=Lax",
      "theme=dark; Path=/",
    ]);
  });
});
