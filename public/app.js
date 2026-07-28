const labels = {
  confirmed: "Codex reset available",
  upcoming: "Codex reset announced soon",
  possible: "Possible Codex reset",
  none: "No Codex reset found",
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

    if (data.bestMatch) {
      evidence.hidden = false;
      document.getElementById("confidence").textContent = `Confidence: ${data.bestMatch.confidence}%`;
      document.getElementById("score").textContent = `Score: ${data.bestMatch.score}`;
      document.getElementById("post-text").textContent = data.bestMatch.text;
      const signals = document.getElementById("signals");
      signals.innerHTML = "";
      for (const signal of data.bestMatch.signals || []) {
        const chip = document.createElement("span");
        chip.textContent = signal;
        signals.appendChild(chip);
      }
      const postLink = document.getElementById("post-link");
      postLink.href = data.bestMatch.url;
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
