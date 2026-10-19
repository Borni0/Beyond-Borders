export function copySetCookieHeaders(source: Headers, target: Headers) {
  const cookies = typeof source.getSetCookie === "function" ? source.getSetCookie() : [];
  for (const cookie of cookies) {
    target.append("set-cookie", cookie);
  }

  const singleCookie = source.get("set-cookie");
  if (singleCookie && cookies.length === 0) {
    target.append("set-cookie", singleCookie);
  }
}
