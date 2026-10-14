/* Course map: topics as nodes, prerequisites as arrows, mastery as colour */
let highlightPath = [];

const NODE_W = 170, NODE_H = 54, GAP_X = 50, GAP_Y = 40, PER_ROW = 4;
const tone = (m) => (m < 0.5 ? "low" : m < 0.75 ? "mid" : "high");

async function renderMap() {
  const { nodes, edges } = await api.graph();
  const svg = document.querySelector("#map");
  const pos = {};
  nodes.forEach((n, i) => {
    const row = Math.floor(i / PER_ROW), col = i % PER_ROW;
    // alternate direction each row so the chain reads as one continuous path
    const x = (row % 2 ? PER_ROW - 1 - col : col) * (NODE_W + GAP_X) + 10;
    pos[n.id] = { x, y: row * (NODE_H + GAP_Y) + 10 };
  });
  const width = PER_ROW * (NODE_W + GAP_X), height = Math.ceil(nodes.length / PER_ROW) * (NODE_H + GAP_Y) + 20;
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);

  const line = (e) => {
    const a = pos[e.from], b = pos[e.to];
    const hot = highlightPath.includes(e.from) && highlightPath.includes(e.to);
    return `<line class="edge${hot ? " hot" : ""}" x1="${a.x + NODE_W / 2}" y1="${a.y + NODE_H / 2}" x2="${b.x + NODE_W / 2}" y2="${b.y + NODE_H / 2}" marker-end="url(#arrow)"/>`;
  };
  const box = (n) => {
    const p = pos[n.id], hot = highlightPath.includes(n.id);
    const label = n.name.length > 22 ? n.name.slice(0, 21) + "…" : n.name;
    return `<g class="node ${tone(n.mastery)}${hot ? " hot" : ""}"><rect x="${p.x}" y="${p.y}" width="${NODE_W}" height="${NODE_H}" rx="10"/>
      <text x="${p.x + 12}" y="${p.y + 24}">${label.replace(/&/g, "&amp;")}</text>
      <text class="pct" x="${p.x + 12}" y="${p.y + 42}">${Math.round(n.mastery * 100)}% mastery</text></g>`;
  };
  svg.innerHTML = `<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#7d8f9c"/></marker></defs>
    ${edges.map(line).join("")}${nodes.map(box).join("")}`;
}
