const API_BASE = "http://127.0.0.1:8000"; //  FastAPI backend

export async function fetchMonthlySummary(userId, month, year) {
  const res = await fetch(`${API_BASE}/users/${userId}/expenses/summary?month=${month}&year=${year}`);
  if (!res.ok) throw new Error("Failed to fetch summary");
  return await res.json();
}

export async function queryAI(userId, query) {
  const res = await fetch(`${API_BASE}/ai/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, query })
  });
  if (!res.ok) throw new Error("Failed to fetch AI response");
  return await res.json();
}