// services/api.js

const API_BASE = "http://127.0.0.1:8000";

// Helper to get auth headers
function getAuthHeaders() {
  const token = localStorage.getItem("access_token");
  return {
    "Content-Type": "application/json",
    ...(token && { Authorization: `Bearer ${token}` })
  };
}

// USER ENDPOINTS

export async function createUser(name, email, password) {
  const response = await fetch(`${API_BASE}/users`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, password })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to create user");
  }
  
  return await response.json();
}

export async function getUserProfile() {
  const response = await fetch(`${API_BASE}/users/me`, {
    headers: getAuthHeaders()
  });
  
  if (!response.ok) {
    throw new Error("Failed to fetch user profile");
  }
  
  return await response.json();
}

export async function deleteUser() {
  const response = await fetch(`${API_BASE}/users/me`, {
    method: "DELETE",
    headers: getAuthHeaders()
  });
  
  if (!response.ok) {
    throw new Error("Failed to delete user");
  }
  
  return await response.json();
}

// EXPENSE ENDPOINTS

//  NO user_id - comes from auth token
//  created_at format: "MM/DD/YYYY" (e.g., "01/14/2026")
export async function createExpense(category_id, amount, description, created_at = null) {
  const body = { category_id, amount, description };
  if (created_at) body.created_at = created_at;
  
  const response = await fetch(`${API_BASE}/expenses`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(body)
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to create expense");
  }
  
  return await response.json();
}

export async function fetchExpenses() {
  const response = await fetch(`${API_BASE}/expenses`, {
    headers: getAuthHeaders()
  });
  
  if (!response.ok) {
    throw new Error("Failed to fetch expenses");
  }
  
  return await response.json();
}

//  Query params: month (required), year (required), day, week, quarter (optional)
export async function fetchExpenseSummary(month, year, day = null, week = null, quarter = null) {
  let url = `${API_BASE}/expenses/summary?month=${month}&year=${year}`;
  if (day) url += `&day=${day}`;
  if (week) url += `&week=${week}`;
  if (quarter) url += `&quarter=${quarter}`;
  
  const response = await fetch(url, {
    headers: getAuthHeaders()
  });
  
  if (!response.ok) {
    throw new Error("Failed to fetch expense summary");
  }
  
  return await response.json();
}

export async function updateExpense(expenseId, updates) {
  const response = await fetch(`${API_BASE}/expenses/${expenseId}`, {
    method: "PUT",
    headers: getAuthHeaders(),
    body: JSON.stringify(updates)
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to update expense");
  }
  
  return await response.json();
}

export async function deleteExpense(expenseId) {
  const response = await fetch(`${API_BASE}/expenses/${expenseId}`, {
    method: "DELETE",
    headers: getAuthHeaders()
  });
  
  if (!response.ok) {
    throw new Error("Failed to delete expense");
  }
  
  return await response.json();
}

// CATEGORY ENDPOINTS

export async function fetchCategories() {
  const response = await fetch(`${API_BASE}/categories`, {
    headers: { "Content-Type": "application/json" }
  });
  
  if (!response.ok) {
    throw new Error("Failed to fetch categories");
  }
  
  return await response.json();
}

export async function createCategory(name) {
  const response = await fetch(`${API_BASE}/categories`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ name })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to create category");
  }
  
  return await response.json();
}

// BUDGET ENDPOINTS

//  NO user_id - comes from auth token
//  category_id can be null for overall budget
//  period: "daily" | "weekly" | "monthly" | "yearly"
//  start_date/end_date format: "MM/DD/YYYY" or null
export async function createBudget(category_id, amount, period, start_date = null, end_date = null, alert_threshold = 0.8) {
  const body = {
    category_id: category_id || null,
    amount,
    period,
    alert_threshold
  };
  if (start_date) body.start_date = start_date;
  if (end_date) body.end_date = end_date;
  
  const response = await fetch(`${API_BASE}/budgets`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(body)
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to create budget");
  }
  
  return await response.json();
}

export async function fetchBudgets(activeOnly = true) {
  const response = await fetch(`${API_BASE}/budgets?active_only=${activeOnly}`, {
    headers: getAuthHeaders()
  });
  
  if (!response.ok) {
    throw new Error("Failed to fetch budgets");
  }
  
  return await response.json();
}

//  Returns budget with spent, limit, remaining, category_name
export async function fetchBudgetStatus() {
  const response = await fetch(`${API_BASE}/budgets/status`, {
    headers: getAuthHeaders()
  });
  
  if (!response.ok) {
    throw new Error("Failed to fetch budget status");
  }
  
  return await response.json();
}

export async function fetchBudgetById(budgetId) {
  const response = await fetch(`${API_BASE}/budgets/${budgetId}`, {
    headers: getAuthHeaders()
  });
  
  if (!response.ok) {
    throw new Error("Failed to fetch budget");
  }
  
  return await response.json();
}

export async function updateBudget(budgetId, updates) {
  const response = await fetch(`${API_BASE}/budgets/${budgetId}`, {
    method: "PUT",
    headers: getAuthHeaders(),
    body: JSON.stringify(updates)
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to update budget");
  }
  
  return await response.json();
}

export async function deleteBudget(budgetId) {
  const response = await fetch(`${API_BASE}/budgets/${budgetId}`, {
    method: "DELETE",
    headers: getAuthHeaders()
  });
  
  if (!response.ok) {
    throw new Error("Failed to delete budget");
  }
  
  return await response.json();
}

// AI ENDPOINTS

//  NO user_id - comes from auth token
//  Body: { query: string }
//  Response: { response: string, data, confidence, suggestions, next_action }
export async function queryAI(query) {
  const response = await fetch(`${API_BASE}/ai/query`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ query })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to query AI");
  }
  
  return await response.json();
}