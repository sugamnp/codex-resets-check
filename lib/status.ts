import { fetchPosts } from "./providers";
import { scorePost } from "./scoring";
import type { ResetStatus, ScoredPost } from "./types";

const MAX_AGE_DAYS = 14;

export async function getResetStatus(): Promise<ResetStatus> {
  const checkedAt = new Date().toISOString();

  try {
    const posts = await fetchPosts();
    const cutoff = Date.now() - MAX_AGE_DAYS * 24 * 60 * 60 * 1000;
    const scored = posts
      .filter((post) => new Date(post.createdAt).getTime() >= cutoff)
      .map(scorePost)
      .sort((a, b) => b.score - a.score);

    const bestMatch = scored.find((post) => post.status !== "unrelated") as ScoredPost | undefined;

    if (!bestMatch) {
      return {
        status: "none",
        summary: `No qualifying announcement was found in posts from the last ${MAX_AGE_DAYS} days.`,
        checkedAt
      };
    }

    return {
      status: bestMatch.status,
      summary: bestMatch.status === "confirmed"
        ? "A high-confidence post announces additional or restored Codex usage."
        : bestMatch.status === "upcoming"
          ? "A post indicates additional or restored Codex usage is expected soon."
          : "A relevant post was found, but it needs a manual check before treating it as confirmed.",
      checkedAt,
      bestMatch
    };
  } catch (error) {
    return {
      status: "unavailable",
      summary: error instanceof Error ? error.message : "The data source could not be checked.",
      checkedAt
    };
  }
}
