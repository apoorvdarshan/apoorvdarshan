const GITHUB_API = "https://api.github.com/repos/";
const USER_AGENT = "apoorvdarshan-github-star-badge-worker";
const CACHE_SECONDS = 60 * 60;
const STALE_SECONDS = 60 * 60 * 24;

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === "/" || url.pathname === "/health") {
      return new Response("GitHub star badge worker is running\n", {
        headers: { "content-type": "text/plain; charset=utf-8" },
      });
    }

    if (url.pathname !== "/api/stars") {
      return new Response("Not found\n", { status: 404 });
    }

    const repo = url.searchParams.get("repo") || "";
    if (!isValidRepo(repo)) {
      return svgResponse(renderBadge("bad", "#e05d44", "Invalid repo"), 400, 300);
    }

    const cacheKey = new Request(new URL(`/api/stars?repo=${repo}`, url.origin), request);
    const cached = await caches.default.match(cacheKey);
    if (cached) {
      return cached;
    }

    try {
      const stars = await getStarCount(repo, env);
      const badge = svgResponse(renderBadge(formatStars(stars)), 200, CACHE_SECONDS, STALE_SECONDS);
      ctx.waitUntil(caches.default.put(cacheKey, badge.clone()));
      return badge;
    } catch (error) {
      console.error(`GitHub API star lookup failed for ${repo}:`, error);

      try {
        const badge = await getShieldsBadge(repo);
        ctx.waitUntil(caches.default.put(cacheKey, badge.clone()));
        return badge;
      } catch (fallbackError) {
        console.error(`Shields fallback failed for ${repo}:`, fallbackError);
        return svgResponse(renderBadge("err", "#e05d44", "GitHub API error"), 502, 300);
      }
    }
  },
};

function isValidRepo(repo) {
  return /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repo);
}

async function getStarCount(repo, env) {
  const headers = {
    accept: "application/vnd.github+json",
    "user-agent": USER_AGENT,
    "x-github-api-version": "2022-11-28",
  };

  if (env.GITHUB_TOKEN) {
    headers.authorization = `Bearer ${env.GITHUB_TOKEN}`;
  }

  const response = await fetch(`${GITHUB_API}${repo}`, { headers });
  if (!response.ok) {
    throw new Error(`GitHub API returned ${response.status}`);
  }

  const data = await response.json();
  if (typeof data.stargazers_count !== "number") {
    throw new Error("GitHub API response did not include stargazers_count");
  }

  return data.stargazers_count;
}

async function getShieldsBadge(repo) {
  const response = await fetch(
    `https://img.shields.io/github/stars/${repo}?style=flat-square&label=%E2%98%85&color=0D7C37`,
    {
      headers: {
        accept: "image/svg+xml",
        "user-agent": USER_AGENT,
      },
    },
  );

  if (!response.ok) {
    throw new Error(`Shields returned ${response.status}`);
  }

  const svg = await response.text();
  if (!svg.includes("<svg")) {
    throw new Error("Shields response was not an SVG");
  }

  return svgResponse(svg, 200, CACHE_SECONDS, STALE_SECONDS);
}

function formatStars(stars) {
  if (stars >= 1_000_000) {
    const value = stars / 1_000_000;
    return `${value >= 10 ? Math.round(value) : trimDecimal(value.toFixed(1))}M`;
  }

  if (stars >= 10_000) {
    return `${Math.round(stars / 1_000)}k`;
  }

  if (stars >= 1_000) {
    return `${trimDecimal((stars / 1_000).toFixed(1))}k`;
  }

  return String(stars);
}

function trimDecimal(value) {
  return value.replace(/\.0$/, "");
}

function renderBadge(value, color = "#0D7C37", description = `★: ${value}`) {
  const leftWidth = 19;
  const rightWidth = value.length * 6 + 13;
  const width = leftWidth + rightWidth;
  const valueX = leftWidth + rightWidth / 2;
  const escapedValue = escapeXml(value);
  const escapedDescription = escapeXml(description);

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="20" role="img" aria-label="${escapedDescription}">
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#fff" stop-opacity=".12"/>
    <stop offset="1" stop-color="#000" stop-opacity=".12"/>
  </linearGradient>
  <clipPath id="r">
    <rect width="${width}" height="20" rx="0" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="${leftWidth}" height="20" fill="#555"/>
    <rect x="${leftWidth}" width="${rightWidth}" height="20" fill="${color}"/>
    <rect width="${width}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="11">
    <text x="9.5" y="15" fill="#010101" fill-opacity=".3">★</text>
    <text x="9.5" y="14">★</text>
    <text x="${valueX}" y="15" fill="#010101" fill-opacity=".3">${escapedValue}</text>
    <text x="${valueX}" y="14">${escapedValue}</text>
  </g>
</svg>`;
}

function svgResponse(svg, status = 200, maxAge = CACHE_SECONDS, staleWhileRevalidate = 0) {
  const cacheControl = [`public`, `max-age=${maxAge}`];
  if (staleWhileRevalidate > 0) {
    cacheControl.push(`stale-while-revalidate=${staleWhileRevalidate}`);
  }

  return new Response(svg, {
    status,
    headers: {
      "content-type": "image/svg+xml; charset=utf-8",
      "cache-control": cacheControl.join(", "),
      "x-content-type-options": "nosniff",
    },
  });
}

function escapeXml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}
