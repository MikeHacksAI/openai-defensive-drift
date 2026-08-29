(() => {
  const start = new Date('2026-08-29T00:00:00-05:00');
  const end = new Date('2026-10-02T23:59:59-05:00');
  const now = new Date();
  const totalDays = 35;
  const elapsedMs = Math.max(0, Math.min(now - start, end - start));
  const elapsedDays = Math.min(totalDays, Math.floor(elapsedMs / 86400000) + 1);
  const percent = Math.max(3, Math.min(100, Math.round((elapsedDays / totalDays) * 100)));

  const label = document.getElementById('progress-label');
  const bar = document.getElementById('progress-bar');
  const gate = document.getElementById('next-gate');

  if (label) label.textContent = `Day ${elapsedDays} of ${totalDays}`;
  if (bar) bar.style.width = `${percent}%`;

  if (gate) {
    if (now < new Date('2026-09-05T00:00:00-05:00')) gate.textContent = 'Next gate: M1 — Research Design Frozen, September 4.';
    else if (now < new Date('2026-09-12T00:00:00-05:00')) gate.textContent = 'Next gate: M2 — Benchmark v0.1 Frozen, September 11.';
    else if (now < new Date('2026-09-19T00:00:00-05:00')) gate.textContent = 'Next gate: M3 — Conventional Baselines Complete, September 18.';
    else if (now < new Date('2026-09-26T00:00:00-05:00')) gate.textContent = 'Next gate: M4 — AI Evaluation Complete, September 25.';
    else if (now <= end) gate.textContent = 'Next gate: M5 — Grant Ready, October 2.';
    else gate.textContent = 'The 35-day pre-grant sprint has reached its grant-readiness review date.';
  }
})();
