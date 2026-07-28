import { describe, expect, it } from "vitest";
import { scorePost } from "../lib/scoring";

const post = (text: string) => ({
  id: "1",
  text,
  createdAt: new Date().toISOString(),
  url: "https://x.com/thsottiaux/status/1"
});

describe("scorePost", () => {
  it("confirms an explicit Codex reset announcement", () => {
    expect(scorePost(post("We have reset Codex usage limits for Plus and Pro users.")).status).toBe("confirmed");
  });

  it("rejects an unrelated laptop reset", () => {
    expect(scorePost(post("I had to reset my laptop today.")).status).toBe("unrelated");
  });

  it("does not accept reset by itself", () => {
    expect(scorePost(post("Reset button pressed.")).status).toBe("unrelated");
  });

  it("marks an explicit future reset as upcoming", () => {
    expect(scorePost(post("We will reset Codex usage limits for all Plus users tomorrow.")).status).toBe("upcoming");
  });

  it("rejects general Codex discussion", () => {
    expect(scorePost(post("Codex is getting better at understanding repositories.")).status).toBe("unrelated");
  });
});
