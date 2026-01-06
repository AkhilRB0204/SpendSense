// services/auth.js
export async function login(email, password) {
  const response = await fetch("http://127.0.0.1:8000/users/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username: email, password }),
  });
  if (!response.ok) throw new Error("Invalid credentials");
  return response.json(); // { access_token, token_type }
}
