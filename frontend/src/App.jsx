// App.jsx
import React, { useEffect, useState } from "react";
import { fetchMonthlySummary, queryAI } from "./services/api";

function App() {
  const [userId, setUserId] = useState(null); // dynamic user
  const [summary, setSummary] = useState(null);
  const [aiResponse, setAiResponse] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const month = new Date().getMonth() + 1;
  const year = new Date().getFullYear();

  const handleLogin = async () => {
    try {
      const { access_token } = await login(email, password);
      localStorage.setItem("token", access_token);

      // Decode JWT to get user email
      const payload = JSON.parse(atob(access_token.split(".")[1]));
      const userEmail = payload.sub;

      // Fetch user ID from backend
      const res = await fetch(`http://127.0.0.1:8000/debug`); // temp way to find user_id
      const data = await res.json();
      const user = data.users.find(u => u.email === userEmail && !u.deleted_at);
      setUserId(user.user_id);
    } catch (err) {
      console.error("Login failed", err);
    }
  };

  useEffect(() => {
    if (!userId) return;

    fetchMonthlySummary(userId, month, year)
      .then(data => setSummary(data))
      .catch(err => console.error(err));

    queryAI(userId, "Show me insights for this month")
      .then(data => setAiResponse(data?.result || "No insights"))
      .catch(err => console.error(err));
  }, [userId]);

  if (!userId) {
    return (
      <div>
        <h2>Login</h2>
        <input placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} />
        <input
          placeholder="Password"
          type="password"
          value={password}
          onChange={e => setPassword(e.target.value)}
        />
        <button onClick={handleLogin}>Login</button>
      </div>
    );
  }

  return (
    <div style={{ padding: "20px" }}>
      <h1>SpendSense Dashboard</h1>
      {/* ...charts and AI insights... */}
    </div>
  );
}

export default App;
