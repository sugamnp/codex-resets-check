import { getResetStatus } from "@/lib/status";

export const dynamic = "force-dynamic";

export default async function Home() {
  const result = await getResetStatus();
  const label = {
    confirmed: "Codex reset available",
    upcoming: "Codex reset announced soon",
    possible: "Possible Codex reset",
    none: "No Codex reset found",
    unavailable: "Unable to check right now"
  }[result.status];

  return (
    <main className="shell">
      <section className="card">
        <p className="eyebrow">Monitoring @thsottiaux</p>
        <h1>Are any Codex resets available or coming soon?</h1>
        <div className={`status status-${result.status}`}>
          <span className="dot" aria-hidden="true" />
          <div><strong>{label}</strong><p>{result.summary}</p></div>
        </div>

        {result.bestMatch ? (
          <article className="evidence">
            <div className="evidenceTop">
              <span>Confidence: {result.bestMatch.confidence}%</span>
              <span>Score: {result.bestMatch.score}</span>
            </div>
            <blockquote>{result.bestMatch.text}</blockquote>
            <p className="reason">{result.bestMatch.explanation}</p>
            <div className="signals">
              {result.bestMatch.signals.map((signal) => <span key={signal}>{signal}</span>)}
            </div>
            <a href={result.bestMatch.url} target="_blank" rel="noreferrer" className="link">View original post on X</a>
          </article>
        ) : null}

        <footer>
          Last checked: {new Date(result.checkedAt).toLocaleString("en-AU", { timeZone: "Australia/Perth" })} AWST
        </footer>
      </section>
    </main>
  );
}
