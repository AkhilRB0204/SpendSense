// App.jsx
import React, { useState } from "react";
import Dashboard from "./Dashboard";
import { login } from "./services/auth";

function App() {
  const [userId, setUserId] = useState(null); // dynamic user
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

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
      setCurrentUser(user);
    } catch (err) {
      console.error("Login failed", err);
    }
  };

  if (!userId) {
    return (
      <div style={{ padding: "20px" }}>
        <h2>Login</h2>
        <input
          placeholder="Email"
          value={email}
          onChange={e => setEmail(e.target.value)}
        />
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
  return <Dashboard userId={userId} />;
}

export default App;
