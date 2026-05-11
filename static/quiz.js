(async function () {
  const quizEl = document.getElementById("quiz");
  const progressEl = document.getElementById("progress");
  const scoreLiveEl = document.getElementById("score-live");
  const resultEl = document.getElementById("result");
  const resultSummary = document.getElementById("result-summary");
  const reviewEl = document.getElementById("review");
  const retryBtn = document.getElementById("retry");

  let questions = [];
  let answers = [];
  let answered = 0;
  let correct = 0;

  async function load() {
    const res = await fetch(`/api/test/${TOPIC_ID}`);
    questions = await res.json();
    answers = new Array(questions.length).fill(null);
    answered = 0;
    correct = 0;
    render();
  }

  function render() {
    quizEl.innerHTML = "";
    resultEl.classList.add("hidden");
    questions.forEach((q, qi) => {
      const card = document.createElement("div");
      card.className = "question";
      card.innerHTML = `
        <div class="num">Pregunta ${qi + 1} de ${questions.length}</div>
        <h3>${escapeHtml(q.q)}</h3>
        <div class="options"></div>
      `;
      const optsEl = card.querySelector(".options");
      q.options.forEach((opt, oi) => {
        const label = document.createElement("label");
        label.className = "option";
        label.innerHTML = `
          <input type="radio" name="q${qi}" value="${oi}">
          <span>${escapeHtml(opt)}</span>
        `;
        label.querySelector("input").addEventListener("change", () => onAnswer(qi, oi, label, optsEl));
        optsEl.appendChild(label);
      });
      quizEl.appendChild(card);
    });
    updateProgress();
  }

  function onAnswer(qi, oi, label, optsEl) {
    if (answers[qi] !== null) return;
    answers[qi] = oi;
    answered++;
    const isOk = oi === questions[qi].answer;
    if (isOk) correct++;
    [...optsEl.children].forEach((el, idx) => {
      el.classList.add("locked");
      const input = el.querySelector("input");
      input.disabled = true;
      if (idx === questions[qi].answer) el.classList.add("correct");
      else if (idx === oi) el.classList.add("wrong");
    });
    updateProgress();
    if (answered === questions.length) showResult();
  }

  function updateProgress() {
    progressEl.textContent = `Respondidas ${answered} / ${questions.length}`;
    scoreLiveEl.textContent = answered > 0 ? `Aciertos: ${correct}` : "";
  }

  function showResult() {
    const total = questions.length;
    const pct = Math.round((correct / total) * 100);
    resultSummary.innerHTML = `
      Aciertos: <strong>${correct} / ${total}</strong> (${pct}%)
      <div class="score-bar"><div style="width:${pct}%"></div></div>
    `;
    reviewEl.innerHTML = "";
    questions.forEach((q, qi) => {
      const user = answers[qi];
      const ok = user === q.answer;
      const item = document.createElement("div");
      item.className = "review-item";
      item.innerHTML = `
        <div class="rq">${qi + 1}. ${escapeHtml(q.q)}</div>
        <div class="ra">✓ ${escapeHtml(q.options[q.answer])}</div>
        ${!ok && user !== null ? `<div class="rw">✗ ${escapeHtml(q.options[user])}</div>` : ""}
      `;
      reviewEl.appendChild(item);
    });
    resultEl.classList.remove("hidden");
    resultEl.scrollIntoView({ behavior: "smooth", block: "start" });

    // Submit score if logged in
    if (typeof USER_LOGGED_IN !== "undefined" && USER_LOGGED_IN) {
      fetch("/api/score", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic_id: TOPIC_ID, correct, total })
      })
        .then(r => r.json())
        .then(() => showToast("✅ Puntuación guardada en el ranking"))
        .catch(() => {});
    }
  }

  function showToast(msg) {
    let t = document.getElementById("_toast");
    if (!t) {
      t = document.createElement("div");
      t.id = "_toast";
      t.className = "toast";
      document.body.appendChild(t);
    }
    t.textContent = msg;
    t.classList.add("show");
    setTimeout(() => t.classList.remove("show"), 3500);
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  retryBtn.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
    load();
  });

  load();
})();
