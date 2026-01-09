const API_BASE = "http://127.0.0.1:8000"; //  FastAPI backend

// Fetch monthly summary
export async function fetchMonthlySummary(userId, month, year) {
  const response = await fetch(
    `${API_BASE}/users/${userId}/expenses/summary?month=${month}&year=${year}`,
    { headers: jsonHeaders() }
  );
  if (!response.ok) throw new Error("Failed to fetch summary");
  return await response.json();
}

// Query AI Endpoint
export async function queryAI(userId, query) {
  const response = await fetch(`${API_BASE}/ai/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, query })
  });
  if (!response.ok) throw new Error("Failed to fetch AI response");
  return await response.json();
}

// Add Expense
export async function addExpense(expenseData) {
  const response = await fetch(`${API_BASE}/expenses`, {
    method: "POST",
    headers: jsonHeaders(),
    body: JSON.stringify(expenseData),
  });
  if (!response.ok) throw new Error("Failed to fetch AI response");
  return await response.json();
}

// Fetch categories
export async function fetchCategories() {
  const response = await fetch(`${API_BASE}/categories`, { headers: jsonHeaders() });
  if (!response.ok) throw new Error("Failed to fetch categories");
  return await response.json();
}