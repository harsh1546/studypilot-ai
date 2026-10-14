/* UI behaviour: navigation, upload, tutor chat, quiz, progress */
const $ = (sel) => document.querySelector(sel);
const el = (tag, cls, html) => { const n = document.createElement(tag); if (cls) n.className = cls; if (html) n.innerHTML = html; return n; };
const esc = (s) => s.replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

/* Link that opens the exact page, slide or timestamp */
function sourceLink(c) {
  const base = `/files/${encodeURIComponent(c.source)}`;
  const href = c.kind === "pdf" ? `${base}#page=${c.anchor}` : base;
  return `<a href="${href}" target="_blank" rel="noopener">${esc(c.source)}, ${esc(c.loc)}</a>`;
}

/* ---------- Navigation ---------- */
document.querySelectorAll(".nav-item").forEach(btn => btn.addEventListener("click", () => {
  document.querySelectorAll(".nav-item, .view").forEach(n => n.classList.remove("is-active"));
  btn.classList.add("is-active");
  $(`#view-${btn.dataset.view}`).classList.add("is-active");
  if (btn.dataset.view === "progress") renderProgress();
  if (btn.dataset.view === "map") renderMap();
}));

/* ---------- Library ---------- */
async function refreshTopics() {
  const topics = await api.topics();
  const grid = $("#topic-grid"), select = $("#quiz-topic");
  grid.innerHTML = ""; select.innerHTML = '<option value="">All topics</option>';
  topics.forEach(t => {
    const card = el("div", "card", `<h3>${esc(t.name)}</h3><p class="meta">${t.size} excerpts${t.prerequisites.length ? " · builds on an earlier topic" : ""}</p>`);
    grid.append(card);
    select.append(new Option(t.name, t.id));
  });
  return topics;
}

async function handleFiles(files) {
  const status = $("#upload-status");
  status.textContent = "Reading your files…";
  try {
    const r = await api.upload(files);
    status.textContent = `Added ${r.units} excerpts across ${r.topics.length} topics.`;
    await refreshTopics();
  } catch (e) { status.textContent = e.message; }
}
$("#file-input").addEventListener("change", e => handleFiles(e.target.files));
const zone = $("#dropzone");
zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("is-over"); });
zone.addEventListener("dragleave", () => zone.classList.remove("is-over"));
zone.addEventListener("drop", e => { e.preventDefault(); zone.classList.remove("is-over"); handleFiles(e.dataTransfer.files); });

/* ---------- Tutor ---------- */
$("#ask-form").addEventListener("submit", async e => {
  e.preventDefault();
  const input = $("#ask-input"), q = input.value.trim();
  if (!q) return;
  input.value = "";
  $("#chat").append(el("div", "msg user", esc(q)));
  try {
    const r = await api.ask(q, $("#ask-lang").value);
    const msg = el("div", `msg${r.covered ? "" : " flag"}`, esc(r.answer));
    r.citations.forEach(c => msg.append(el("span", "cite", `[${c.n}] ${sourceLink(c)}: ${esc(c.text)}`)));
    $("#chat").append(msg);
  } catch (err) { $("#chat").append(el("div", "msg flag", esc(err.message))); }
});

/* ---------- Quiz ---------- */
let sessionAsked = 0;
let sessionCorrect = 0;
async function nextQuestion() {
  const card = $("#quiz-card"), topic = $("#quiz-topic").value;
  const limit = Number($("#quiz-count")?.value || 10);
  if (sessionAsked >= limit) {
    card.innerHTML = `<div class="feedback"><strong>Session complete</strong><p>You answered ${sessionAsked} questions and got ${sessionCorrect} correct (${Math.round(sessionCorrect / Math.max(1, sessionAsked) * 100)}%). Choose a new session length or restart to keep practising.</p><button class="btn" id="quiz-restart">Start another session</button></div>`;
    $("#quiz-restart").addEventListener("click", () => { sessionAsked = 0; sessionCorrect = 0; nextQuestion(); });
    return;
  }
  try {
    const q = await api.quiz(topic === "" ? null : Number(topic), $("#quiz-kind").value);
    card.innerHTML = `<div class="tags"><span class="tag">${q.difficulty}</span><span class="tag">${sourceLink(q.source)}</span></div><p>${esc(q.question)}</p>`;
    const body = el("div", "options");
    if (q.options) q.options.forEach(o => {
      const b = el("button", "option", esc(o));
      b.addEventListener("click", () => submit(q, o, body, b));
      body.append(b);
    });
    else {
      const input = el("input"); input.type = "text"; input.placeholder = "Your answer";
      const go = el("button", "btn", "Check answer");
      go.addEventListener("click", () => submit(q, input.value, body, null));
      body.append(input, go);
    }
    card.append(body);
  } catch (e) { card.innerHTML = `<p class="empty">${esc(e.message)}</p>`; }
}

async function submit(q, response, body, chosen) {
  const r = await api.answer(q.id, response);
  sessionAsked += 1;
  if (r.correct) sessionCorrect += 1;
  body.querySelectorAll("button, input").forEach(n => n.disabled = true);
  if (chosen) chosen.classList.add(r.correct ? "is-right" : "is-wrong");
  body.querySelectorAll(".option").forEach(o => { if (o.textContent === r.answer) o.classList.add("is-right"); });
  body.append(el("div", "feedback", `<strong>${r.correct ? "Correct — nicely done." : `Not quite. The answer is ${esc(r.answer)}.`}</strong>
    <p>${esc(r.explanation || "Review the cited excerpt to reinforce this concept.")}</p>
    <p class="meta">Source: ${sourceLink({ ...r.source })}. Topic mastery is now ${Math.round(r.mastery * 100)}%. Session score: ${sessionCorrect}/${sessionAsked}.</p>`));
  if (r.remedial) showRemedial(body, r.remedial);
}
$("#quiz-start").addEventListener("click", nextQuestion);

/* Root-cause help: teach the weak prerequisite, then let the student retry */
function showRemedial(body, rem) {
  highlightPath = rem.path;
  const box = el("div", "feedback remedial", `<strong>Start with ${esc(rem.topic)}.</strong> This earlier topic looks like the real gap.<p>${esc(rem.answer)}</p>`);
  rem.citations.forEach(c => box.append(el("span", "cite", `[${c.n}] ${sourceLink(c)}: ${esc(c.text)}`)));
  body.append(box);
}

/* ---------- Progress ---------- */
async function renderProgress() {
  const [topics, report] = await Promise.all([api.topics(), api.report()]);
  const bars = $("#mastery-bars");
  bars.innerHTML = topics.length ? "" : '<p class="empty">Upload material to see your topics.</p>';
  topics.forEach(t => bars.append(el("div", "bar-row",
    `<span>${esc(t.name)}</span><div class="bar"><span class="${t.mastery < .5 ? "low" : ""}" style="width:${t.mastery * 100}%"></span></div><span>${Math.round(t.mastery * 100)}%</span>`)));
  const fill = (id, rows, empty) => { const ul = $(id); ul.innerHTML = rows.length ? rows.map(r => `<li>${r}</li>`).join("") : `<li>${empty}</li>`; };
  fill("#weak-list", report.weak.map(w => `${esc(w.topic)} (${Math.round(w.mastery * 100)}%)`), "Nothing yet.");
  fill("#mistake-list", report.mistakes.map(m => `${esc(m.topic)}: ${esc(m.note)}`), "No mistakes recorded.");
}
