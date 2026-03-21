/* ════════════════════════════════════════════════════════════════
   Yahoo Finance Crumb Authentication
   
   Yahoo's v10 quoteSummary API requires a crumb + cookie pair.
   Steps:
     1. GET https://fc.yahoo.com/ → extract A3 cookie from set-cookie
     2. GET https://query2.finance.yahoo.com/v1/test/getcrumb with cookie
   Cache for 1 hour; retry once on failure.
   ════════════════════════════════════════════════════════════════ */

let _crumb: string | null = null;
let _cookie: string | null = null;
let _crumbExpiry = 0;

const UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36";

export interface YahooAuth {
  crumb: string;
  cookie: string;
}

/**
 * Obtain a fresh Yahoo Finance crumb + cookie pair.
 * Returns null if authentication cannot be established.
 */
async function fetchFreshCrumb(): Promise<YahooAuth | null> {
  try {
    // Step 1: Get cookie from fc.yahoo.com
    const cookieResp = await fetch("https://fc.yahoo.com/", {
      redirect: "manual",
      headers: { "User-Agent": UA },
    });
    const setCookie = cookieResp.headers.get("set-cookie") || "";

    // Extract A3 cookie (primary auth cookie)
    const cookieMatch = setCookie.match(/A3=[^;]+/);
    let cookie: string;
    if (!cookieMatch) {
      // Fallback: try any cookie that looks useful
      const anyMatch = setCookie.match(/[A-Z]\d?=[^;]+/);
      if (!anyMatch) return null;
      cookie = anyMatch[0];
    } else {
      cookie = cookieMatch[0];
    }

    // Step 2: Get crumb using cookie
    const crumbResp = await fetch(
      "https://query2.finance.yahoo.com/v1/test/getcrumb",
      {
        headers: {
          Cookie: cookie,
          "User-Agent": UA,
        },
      },
    );

    if (!crumbResp.ok) return null;

    const crumb = await crumbResp.text();
    if (!crumb || crumb.includes("error") || crumb.includes("<") || crumb.length > 50) {
      return null;
    }

    return { crumb: crumb.trim(), cookie };
  } catch {
    return null;
  }
}

/**
 * Get a cached or fresh Yahoo crumb + cookie.
 * Cached for 1 hour. Returns null if auth fails.
 */
export async function getYahooCrumb(): Promise<YahooAuth | null> {
  const now = Date.now();
  if (_crumb && _cookie && now < _crumbExpiry) {
    return { crumb: _crumb, cookie: _cookie };
  }

  const auth = await fetchFreshCrumb();
  if (auth) {
    _crumb = auth.crumb;
    _cookie = auth.cookie;
    _crumbExpiry = now + 3600_000; // 1 hour
    return auth;
  }

  return null;
}

/**
 * Invalidate the cached crumb (e.g. after a 401/403 response).
 */
export function invalidateYahooCrumb(): void {
  _crumb = null;
  _cookie = null;
  _crumbExpiry = 0;
}

/**
 * Fetch Yahoo quoteSummary with crumb authentication.
 * Retries once with a fresh crumb on 401/403.
 * Returns null on failure.
 */
export async function fetchQuoteSummary(
  symbol: string,
  modules: string[] = ["defaultKeyStatistics", "financialData"],
): Promise<Record<string, unknown> | null> {
  for (let attempt = 0; attempt < 2; attempt++) {
    const auth = await getYahooCrumb();
    if (!auth) return null;

    try {
      const url = `https://query2.finance.yahoo.com/v10/finance/quoteSummary/${encodeURIComponent(symbol)}?modules=${modules.join(",")}&crumb=${encodeURIComponent(auth.crumb)}`;
      const resp = await fetch(url, {
        headers: {
          Cookie: auth.cookie,
          "User-Agent": UA,
        },
      });

      if (resp.status === 401 || resp.status === 403) {
        // Crumb expired or invalid — retry with fresh crumb
        invalidateYahooCrumb();
        continue;
      }

      if (!resp.ok) return null;

      const json = await resp.json();
      const result = json?.quoteSummary?.result?.[0];
      return result ?? null;
    } catch {
      return null;
    }
  }

  return null;
}
