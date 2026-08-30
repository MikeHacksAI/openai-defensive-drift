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

  if (label) label.textContent = `Day ${elapsedDays} of ${totalDays}`;
  if (bar) bar.style.width = `${percent}%`;

  const setText = (selector, value) => {
    const element = document.querySelector(selector);
    if (element && value !== undefined && value !== null) {
      element.textContent = String(value);
    }
  };

  const renderStatus = (status) => {
    setText('#status h2', status.headline);
    setText('#status .status-layout > div > p', status.detail);
    setText(
      '#next-gate',
      `Active gate: ${status.milestone} — ${status.next_gate} Latest-acceptable completion: ${status.latest_acceptable_completion}.`
    );

    if (status.core_review) {
      setText('.stats article:first-child .stat-value', `${status.core_review.reviewed}/${status.core_review.target}`);
      setText('.stats article:first-child .stat-label', 'core evidence packets human-reviewed');
    }
  };

  fetch('./status.json', { cache: 'no-store' })
    .then((response) => {
      if (!response.ok) throw new Error(`status.json HTTP ${response.status}`);
      return response.json();
    })
    .then(renderStatus)
    .catch((error) => {
      console.error('Defensive Drift public status could not be loaded:', error);
    });
})();
