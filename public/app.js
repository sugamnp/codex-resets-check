const labels = {
  confirmed: "Codex reset available",
  upcoming: "Codex reset announced soon",
  possible: "Possible Codex reset",
  none: "No current Codex reset",
  unavailable: "Unable to check right now",
};

async function loadStatus() {
  const statusBox = document.getElementById("status");
  const label = document.getElementById("status-label");
  const summary = document.getElementById("status-summary");
  const checkedAt = document.getElementById("checked-at");
  const evidence = document.getElementById("evidence");

  try {
    const response = await fetch(`status.json?v=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();

    statusBox.className = `status status-${data.status}`;
    label.textContent = labels[data.status] || "Unknown status";
    summary.textContent = data.summary || "No summary available.";

    const date = new Date(data.checkedAt);
    checkedAt.textContent = `Last checked: ${date.toLocaleString("en-AU", { timeZone: "Australia/Perth" })} AWST`;

    const displayMatch = data.bestMatch || data.lastReset;
    if (displayMatch) {
      evidence.hidden = false;

      const matchDate = new Date(displayMatch.createdAt);
      const resetDateText = matchDate.toLocaleString("en-AU", { timeZone: "Australia/Perth" });

      document.getElementById("confidence").textContent = data.bestMatch
        ? `Confidence: ${displayMatch.confidence || 95}%`
        : `Last confirmed reset: ${resetDateText} AWST`;
      document.getElementById("score").textContent = data.bestMatch
        ? `Score: ${displayMatch.score || 95}`
        : "Historical confirmed reset";
      document.getElementById("post-text").textContent = displayMatch.text;

      const signals = document.getElementById("signals");
      signals.innerHTML = "";
      const signalList = data.bestMatch
        ? (displayMatch.signals || [])
        : ["Most recent confirmed reset", "No newer active reset detected"];

      for (const signal of signalList) {
        const chip = document.createElement("span");
        chip.textContent = signal;
        signals.appendChild(chip);
      }

      const postLink = document.getElementById("post-link");
      postLink.href = displayMatch.url;
      postLink.textContent = data.bestMatch ? "View reset source" : "View last reset source";
    } else {
      evidence.hidden = true;
    }
  } catch (error) {
    statusBox.className = "status status-unavailable";
    label.textContent = labels.unavailable;
    summary.textContent = "The published status file could not be loaded.";
    checkedAt.textContent = "Last checked: unavailable";
    evidence.hidden = true;
  }
}

loadStatus();
