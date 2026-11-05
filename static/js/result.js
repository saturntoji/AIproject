"use strict";
// Рендер результата. Пользовательский текст выводится только через textContent.

const CATEGORY_VIEW = {
  SAFE: { css: "safe", icon: "✓", sms: "Безопасное сообщение", url: "Безопасная ссылка", badge: "Безопасно" },
  SUSPICIOUS: { css: "warn", icon: "!", sms: "Подозрительное сообщение", url: "Подозрительная ссылка", badge: "Подозрительно" },
  FRAUDULENT: { css: "danger", icon: "⚠", sms: "Мошенническое сообщение", url: "Опасная ссылка", badge: "Мошенничество" },
  DANGEROUS: { css: "danger", icon: "⚠", sms: "Опасная ссылка", url: "Опасная ссылка", badge: "Опасная" },
};
const LEVEL_NAMES = { LOW: "низкий", MEDIUM: "средний", HIGH: "высокий" };
const LANGUAGE_NAMES = { ru: "русский", kk: "казахский", en: "английский", other: "другой" };

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function badge(category) {
  const view = CATEGORY_VIEW[category];
  return el("span", `badge-risk badge-${view.css}`, `${view.icon} ${view.badge}`);
}

function formatProbability(value) {
  return value.toFixed(2).replace(".", ",");
}

// Ссылка показывается неактивным текстом, домен выделяется.
function urlText(url, domain) {
  const box = el("span", "url-text");
  const start = domain ? url.toLowerCase().indexOf(domain.toLowerCase()) : -1;
  if (start < 0) {
    box.textContent = url;
    return box;
  }
  box.append(url.slice(0, start), el("mark", "", url.slice(start, start + domain.length)), url.slice(start + domain.length));
  return box;
}

function featureTable(rows) {
  const grid = el("div", "feature-grid");
  for (const row of rows) {
    const line = el("div", row.triggered ? "feature-row triggered" : "feature-row");
    let value = String(row.value);
    if (row.is_flag) value = row.value ? "да" : "нет";
    else if (!Number.isInteger(row.value)) value = row.value.toFixed(2).replace(".", ",");
    line.append(el("span", "", row.title), el("span", "", value));
    grid.append(line);
  }
  return grid;
}

function renderResult(data, container) {
  const view = CATEGORY_VIEW[data.category];
  const isUrl = data.type === "URL";
  const root = el("section", `result result-${view.css}`);

  const head = el("div", "result-head");
  head.append(
    el("span", "result-title", `${view.icon} ${isUrl ? view.url : view.sms}`),
    el("span", "", `Риск: ${LEVEL_NAMES[data.risk_level]}`)
  );
  root.append(head);

  const body = el("div", "result-body");
  const scoreRow = el("div", "score-row");
  const track = el("div", "score-track");
  const fill = el("div", "score-fill");
  fill.style.width = `${data.risk_score}%`;
  track.append(fill);
  scoreRow.append(el("span", "", "Risk Score"), track, el("span", "score-value", `${data.risk_score} / 100`));
  body.append(scoreRow);

  for (const note of data.warnings) body.append(el("div", "note", note));

  if (!isUrl) {
    body.append(el("div", "section-label", data.is_masked ? "Текст (маскирован, полный текст не хранится)" : "Текст сообщения"));
    body.append(el("div", "input-echo", data.input));
    body.append(el("div", "prob-line", `Язык: ${LANGUAGE_NAMES[data.language] || data.language}`));
    const line = el("div", "prob-line", `Вероятность мошенничества по тексту (SMS-модель): ${formatProbability(data.p_sms)}`);
    if (!data.p_sms_reliable) line.append(el("span", "tag-unreliable", "ненадёжно"));
    body.append(line);
  }
  if (data.p_url_max !== null) {
    body.append(el("div", "prob-line", `Вероятность опасности ссылки (P_url): ${formatProbability(data.p_url_max)}`));
  }

  if (isUrl && data.urls.length) {
    const item = data.urls[0];
    const row = el("div", "url-item mt-2");
    row.append(urlText(item.url, item.domain));
    body.append(row, el("div", "prob-line", `Домен: ${item.domain}`));
    body.append(el("div", "section-label", "Признаки URL"), featureTable(item.feature_table));
  } else if (data.urls.length) {
    body.append(el("div", "section-label", "Найденные ссылки (не открываются, проверены отдельно)"));
    for (const item of data.urls) {
      const row = el("div", "url-item");
      row.append(urlText(item.url, item.domain), badge(item.category));
      body.append(row);
    }
  }

  if (data.features.length) {
    body.append(el("div", "section-label", "Признаки социальной инженерии"));
    const list = el("div");
    list.append(el("span", "", data.features.map((f) => f.title).join(" · ")));
    body.append(list);
  }

  body.append(el("div", "section-label", "Почему такой результат"));
  const reasons = el("ul", "reasons");
  for (const reason of data.explanation) reasons.append(el("li", "", reason));
  body.append(reasons);

  const recommendation = el("div", "recommendation");
  recommendation.append(el("strong", "", `Рекомендация: ${data.recommendation}`));
  recommendation.append(el("span", "muted", data.disclaimer));
  recommendation.append(el("span", "muted", ` Дата проверки: ${new Date(data.created_at).toLocaleString("ru-RU")}.`));
  body.append(recommendation);

  root.append(body);
  container.replaceChildren(root);
}
