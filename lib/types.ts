export type Post = {
  id: string;
  text: string;
  createdAt: string;
  url: string;
  conversationText?: string;
};

export type MatchStatus =
  | "confirmed"
  | "upcoming"
  | "possible"
  | "none"
  | "unavailable";

export type ScoredPost = Post & {
  score: number;
  confidence: number;
  status: Exclude<MatchStatus, "none" | "unavailable"> | "unrelated";
  signals: string[];
  explanation: string;
};

export type ResetStatus = {
  status: MatchStatus;
  summary: string;
  checkedAt: string;
  bestMatch?: ScoredPost;
};
