"use strict";
(function () {
  const form = document.getElementById("check-form");
  const input = document.getElementById("check-input");
  const submit = document.getElementById("check-submit");
  const errorBox = document.getElementById("check-error");
  const resultBox = document.getElementById("result");
  const counter = document.getElementById("char-counter");
  const clear = document.getElementById("check-clear");
  const kind = form.dataset.kind;
  const submitLabel = submit.textContent;

  function updateCounter() {
    if (counter) counter.textContent = `${input.value.length} / 1000`;
  }

  input.addEventListener("input", updateCounter);
  if (clear) {
    clear.addEventListener("click", () => {
      input.value = "";
      errorBox.textContent = "";
      resultBox.replaceChildren();
      updateCounter();
      input.focus();
    });
  }
  document.querySelectorAll("[data-example]").forEach((button) => {
    button.addEventListener("click", () => {
      input.value = button.dataset.example;
      updateCounter();
    });
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.textContent = "";
    if (!input.value.trim()) {
      errorBox.textContent = kind === "sms" ? "Введите текст сообщения." : "Введите ссылку.";
      return;
    }
    submit.disabled = true;
    submit.textContent = "Анализируем…";
    try {
      const response = await fetch(form.dataset.endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": form.querySelector("[name=csrfmiddlewaretoken]").value,
        },
        body: JSON.stringify(kind === "sms" ? { text: input.value } : { url: input.value }),
      });
      const data = await response.json();
      if (response.ok) {
        renderResult(data, resultBox);
      } else {
        errorBox.textContent = data.error ? data.error.message : "Не удалось выполнить проверку.";
      }
    } catch (error) {
      errorBox.textContent = "Сервер недоступен. Попробуйте ещё раз.";
    } finally {
      submit.disabled = false;
      submit.textContent = submitLabel;
    }
  });
  updateCounter();
})();
