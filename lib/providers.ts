import type { Post } from "./types";

const DEFAULT_INSTANCES = [
  "https://xcancel.com",
  "https://nitter.poast.org",
  "https://nitter.privacydev.net"
];

function decodeXml(value: string): string {
  return value
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function extractTag(item: string, tag: string): string | undefined {
  const match = item.match(new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`, "i"));
  return match?.[1] ? decodeXml(match[1]) : undefined;
}

function parseRss(xml: string): Post[] {
  const items = xml.match(/<item\b[\s\S]*?<\/item>/gi) ?? [];
  return items.flatMap((item) => {
    const text = extractTag(item, "title") || extractTag(item, "description");
    const link = extractTag(item, "link");
    const published = extractTag(item, "pubDate");
    const guid = extractTag(item, "guid");
    if (!text || !link || !published) return [];
    return [{
      id: guid || link,
      text,
      createdAt: new Date(published).toISOString(),
      url: link.replace(/^https?:\/\/[^/]+/, "https://x.com")
    }];
  });
}

async function fetchFromInstance(instance: string, username: string): Promise<Post[]> {
  const response = await fetch(`${instance.replace(/\/$/, "")}/${username}/rss`, {
    headers: {
      "User-Agent": "Mozilla/5.0 (compatible; CodexResetWatch/1.0)",
      Accept: "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8"
    },
    signal: AbortSignal.timeout(8000),
    cache: "no-store"
  });
  if (!response.ok) throw new Error(`${instance} returned ${response.status}`);
  const posts = parseRss(await response.text());
  if (posts.length === 0) throw new Error(`${instance} returned no posts`);
  return posts;
}

export async function fetchPosts(): Promise<Post[]> {
  if (process.env.POST_PROVIDER === "mock") {
    return [{
      id: "mock-1",
      text: "We have reset Codex usage limits for Plus and Pro users. Enjoy building.",
      createdAt: new Date().toISOString(),
      url: "https://x.com/thsottiaux"
    }];
  }

  const username = process.env.X_USERNAME || "thsottiaux";
  const configured = process.env.NITTER_INSTANCES?.split(",").map((v) => v.trim()).filter(Boolean);
  const instances = configured?.length ? configured : DEFAULT_INSTANCES;
  const failures: string[] = [];

  for (const instance of instances) {
    try {
      return await fetchFromInstance(instance, username);
    } catch (error) {
      failures.push(error instanceof Error ? error.message : String(error));
    }
  }

  throw new Error(`All public RSS sources failed: ${failures.join("; ")}`);
}
