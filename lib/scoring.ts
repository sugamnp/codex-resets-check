import type { Post, ScoredPost } from "./types";

type Rule = { id: string; points: number; pattern: RegExp; signal: string };

const positiveRules: Rule[] = [
  { id: "codex", points: 30, pattern: /\bcodex\b/i, signal: "Explicitly mentions Codex" },
  { id: "usage-limits", points: 22, pattern: /\b(?:usage|rate|message|token|credit)s?\s+(?:limit|cap|allowance)s?\b|\blimits?\b/i, signal: "Mentions usage limits or credits" },
  { id: "reset-action", points: 22, pattern: /\b(?:reset|resetting|reset(?:ted)?|refill(?:ed)?|replenish(?:ed)?|restore(?:d)?)\b/i, signal: "Describes a reset or replenishment" },
  { id: "increase-action", points: 18, pattern: /\b(?:increase(?:d|s|ing)?|double(?:d)?|boost(?:ed|ing)?|more|extra|additional|higher)\b/i, signal: "Describes increased availability" },
  { id: "free-access", points: 22, pattern: /\b(?:free|complimentary|on us|unlimited)\b/i, signal: "Mentions free or unlimited access" },
  { id: "user-scope", points: 12, pattern: /\b(?:everyone|all users|plus|pro|free users|teams?|business|enterprise|developers?)\b/i, signal: "Identifies affected users or plans" },
  { id: "announcement", points: 10, pattern: /\b(?:we(?:'ve| have| are|'re| will)|available now|starting today|live now|rolled out|shipped)\b/i, signal: "Sounds like an official announcement" },
  { id: "future", points: 10, pattern: /\b(?:soon|tomorrow|later today|this week|this weekend|next week|coming|will)\b/i, signal: "Contains an upcoming timeframe" }
];

const negativeRules: Rule[] = [
  { id: "unrelated-reset", points: -45, pattern: /\b(?:password|laptop|computer|phone|device|router|server|database|branch|commit|factory)\s+reset\b|\breset\s+(?:my|the)\s+(?:password|laptop|computer|phone|device|router|server|database)\b/i, signal: "Reset appears unrelated to Codex usage" },
  { id: "question", points: -16, pattern: /\?|^(?:does|do|did|will|can|could|is|are|when|anyone)\b/i, signal: "Post appears to be a question" },
  { id: "speculation", points: -18, pattern: /\b(?:maybe|might|hope|hopefully|wish|rumou?r|guess|probably)\b/i, signal: "Post is speculative" },
  { id: "third-party", points: -12, pattern: /\b(?:someone said|people are saying|heard that|apparently)\b/i, signal: "Relies on third-party claims" }
];

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

export function scorePost(post: Post): ScoredPost {
  const fullText = [post.text, post.conversationText].filter(Boolean).join("\n");
  let score = 0;
  const signals: string[] = [];
  const matched = new Set<string>();

  for (const rule of [...positiveRules, ...negativeRules]) {
    if (rule.pattern.test(fullText)) {
      score += rule.points;
      signals.push(rule.signal);
      matched.add(rule.id);
    }
  }

  const hasCodex = matched.has("codex");
  const hasUsageMeaning = matched.has("usage-limits") || matched.has("free-access") || matched.has("increase-action");
  const hasGrantAction = matched.has("reset-action") || matched.has("increase-action") || matched.has("free-access");

  if (!hasCodex) score = Math.min(score, 24);
  if (!hasUsageMeaning) score = Math.min(score, 44);
  if (!hasGrantAction) score = Math.min(score, 44);

  const qualifies = hasCodex && hasUsageMeaning && hasGrantAction;
  const isFuture = matched.has("future");
  const confidence = clamp(Math.round((score / 96) * 100), 0, 99);

  let status: ScoredPost["status"] = "unrelated";
  if (qualifies && score >= 72 && !isFuture) status = "confirmed";
  else if (qualifies && score >= 68 && isFuture) status = "upcoming";
  else if (qualifies && score >= 50) status = "possible";

  const explanation = status === "confirmed"
    ? "The post explicitly connects Codex with added, restored, reset, or free usage and reads as a current announcement."
    : status === "upcoming"
      ? "The post explicitly connects Codex with added or reset usage and includes a future timeframe."
      : status === "possible"
        ? "The required Codex and usage signals are present, but the wording is not strong enough to call it confirmed."
        : "The post does not clearly announce additional or restored Codex usage.";

  return { ...post, score, confidence, status, signals, explanation };
}
