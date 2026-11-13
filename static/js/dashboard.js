"use strict";
(function () {
  const root = document.getElementById("stats-root");
  const emptyBox = document.getElementById("stats-empty");
  const period = document.getElementById("period");
  const COLORS = { safe: "#1a7f37", warn: "#d68a00", danger: "#c62f2f", neutral: "#5b8def" };
  const GRID = "#eceff3";
  const TICKS = "#5b6472";
  const charts = {};

  function setText(id, value) {
    const node = document.getElementById(id);
    if (node) node.textContent = value;
  }

  function draw(id, config) {
    const canvas = document.getElementById(id);
    if (!canvas) return;
    if (charts[id]) charts[id].destroy();
    charts[id] = new Chart(canvas, config);
  }

  function barOptions(extra) {
    return Object.assign({
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { color: TICKS, maxRotation: 0, autoSkipPadding: 16 } },
        y: { beginAtZero: true, grid: { color: GRID }, ticks: { color: TICKS, precision: 0 } },
      },
    }, extra);
  }

  // Подпись по центру кольца: общее число проверок.
  const centerTotal = {
    id: "centerTotal",
    afterDraw(chart) {
      const { ctx, chartArea } = chart;
      const total = chart.data.datasets[0].data.reduce((sum, value) => sum + value, 0);
      ctx.save();
      ctx.font = "700 20px system-ui, sans-serif";
      ctx.fillStyle = "#1b1f27";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(String(total), (chartArea.left + chartArea.right) / 2, (chartArea.top + chartArea.bottom) / 2);
      ctx.restore();
    },
  };

  function drawDashboard(data) {
    setText("stat-total", data.total);
    setText("stat-safe", data.safe);
    setText("stat-suspicious", data.suspicious);
    setText("stat-fraudulent", data.fraudulent);
    setText("days-title", `Проверки за ${data.days} дней`);
    const percent = (value) => `${Math.round((value / data.total) * 100)}%`;

    draw("chart-categories", {
      type: "doughnut",
      data: {
        labels: [
          `Безопасные ${percent(data.safe)}`,
          `Подозрительные ${percent(data.suspicious)}`,
          `Мошеннические ${percent(data.fraudulent)}`,
        ],
        datasets: [{
          data: [data.safe, data.suspicious, data.fraudulent],
          backgroundColor: [COLORS.safe, COLORS.warn, COLORS.danger],
          borderColor: "#ffffff",
          borderWidth: 2,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "62%",
        plugins: { legend: { position: "right", labels: { color: "#1b1f27", boxWidth: 12 } } },
      },
      plugins: [centerTotal],
    });

    const lineSeries = [
      ["Безопасные", "safe", COLORS.safe],
      ["Подозрительные", "suspicious", COLORS.warn],
      ["Мошеннические", "fraudulent", COLORS.danger],
    ];
    draw("chart-days", {
      type: "line",
      data: {
        labels: data.per_day.map((row) => new Date(`${row.date}T00:00:00`).toLocaleDateString("ru-RU", { day: "numeric", month: "short" })),
        datasets: lineSeries.map(([label, key, color]) => ({
          label,
          data: data.per_day.map((row) => row[key]),
          borderColor: color,
          backgroundColor: color,
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 4,
          tension: 0,
        })),
      },
      options: barOptions({
        interaction: { mode: "index", intersect: false },
        plugins: { legend: { position: "top", labels: { color: "#1b1f27", boxWidth: 12 } } },
      }),
    });

    const modelsPanel = document.getElementById("models-panel");
    if (modelsPanel) {
      const models = data.models || [];
      modelsPanel.hidden = models.length === 0;
      const modelsBody = document.getElementById("models-body");
      modelsBody.replaceChildren();
      const fmt = (value) => (value === null || value === undefined ? "—" : Number(value).toFixed(3).replace(".", ","));
      for (const model of models) {
        const tr = document.createElement("tr");
        tr.append(
          el("td", "", model.type), el("td", "", model.version), el("td", "", model.algorithm),
          el("td", "", fmt(model.threshold)), el("td", "", fmt(model.metrics.Precision)),
          el("td", "", fmt(model.metrics.Recall)), el("td", "", fmt(model.metrics.F1)),
        );
        modelsBody.append(tr);
      }
    }

    const body = document.getElementById("recent-body");
    const panel = document.getElementById("recent-panel");
    if (body) {
      panel.hidden = data.is_admin || data.recent.length === 0;
      body.replaceChildren();
      for (const row of data.recent) {
        const tr = document.createElement("tr");
        const date = el("td", "text-nowrap", new Date(row.created_at).toLocaleString("ru-RU", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }));
        const fragmentCell = document.createElement("td");
        const link = el("a", "row-link", row.fragment);
        link.href = row.url;
        fragmentCell.append(link);
        const badgeCell = document.createElement("td");
        badgeCell.append(badge(row.category));
        tr.append(date, el("td", "", row.type), fragmentCell, badgeCell);
        body.append(tr);
      }
    }
  }

  function drawStats(data) {
    setText("stat-sms", data.total_sms);
    setText("stat-url", data.total_url);
    setText("stat-average", data.average_score);
    if (!data.top_features.length) {
      const featuresCanvas = document.getElementById("chart-features");
      if (featuresCanvas) featuresCanvas.closest("section").hidden = true;
    }
    draw("chart-levels", {
      type: "bar",
      data: {
        labels: ["Низкий", "Средний", "Высокий"],
        datasets: [{ label: "Проверок", data: [data.levels.LOW, data.levels.MEDIUM, data.levels.HIGH], backgroundColor: [COLORS.safe, COLORS.warn, COLORS.danger], borderRadius: 4, maxBarThickness: 64 }],
      },
      options: barOptions(),
    });
    draw("chart-features", {
      type: "bar",
      data: {
        labels: data.top_features.map((row) => row.title),
        datasets: [{ label: "Срабатываний", data: data.top_features.map((row) => row.count), backgroundColor: COLORS.neutral, borderRadius: 4, maxBarThickness: 24 }],
      },
      options: barOptions({ indexAxis: "y", scales: { x: { beginAtZero: true, grid: { color: GRID }, ticks: { color: TICKS, precision: 0 } }, y: { grid: { display: false }, ticks: { color: TICKS } } } }),
    });
  }

  async function load() {
    const response = await fetch(`${root.dataset.endpoint}?days=${period.value}`, { headers: { Accept: "application/json" } });
    if (!response.ok) return;
    const data = await response.json();
    emptyBox.hidden = data.total > 0;
    root.hidden = data.total === 0;
    if (data.total === 0) return;
    drawDashboard(data);
    drawStats(data);
  }

  period.addEventListener("change", load);
  load();
})();
