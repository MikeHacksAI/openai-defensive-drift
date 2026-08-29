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
})();
