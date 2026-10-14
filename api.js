/* Thin fetch wrappers for the StudyPilot API */
const api = {
  async json(url, body) {
    const res = await fetch(url, body ? {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    } : undefined);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Request failed");
    return data;
  },
  async upload(files) {
    const form = new FormData();
    [...files].forEach(f => form.append("files", f));
    const res = await fetch("/api/upload", { method: "POST", body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Upload failed");
    return data;
  },
  topics: () => api.json("/api/topics"),
  ask: (question, lang) => api.json("/api/ask", { question, lang }),
  graph: () => api.json("/api/graph"),
  quiz: (topic, kind) => api.json("/api/quiz", { topic, kind }),
  answer: (question_id, response) => api.json("/api/answer", { question_id, response }),
  report: () => api.json("/api/report"),
};
