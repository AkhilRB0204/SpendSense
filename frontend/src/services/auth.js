// services/auth.js
const API_BASE = "http://127.0.0.1:8000";

export async function login(email, password) {
  const response = await fetch(`${API_BASE}/users/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Invalid credentials");
  }
  const data = await response.json(); 

  if (data.access_token) {
    localStorage.setItem("access_token", data.access_token);
  }

  return data; // { access_token, token_type }
}

export function getToken() {
  return localStorage.getItem("access_token");
}

export function logout() {
  localStorage.removeItem("access_token");
}
