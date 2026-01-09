import React, { useEffect, useState } from "react";
import { fetchMonthlySummary, queryAI } from "./services/api";
import Chat from "./chat";

function Home({ userId }) {
  const [summary, setSummary] = useState(null);
  const [aiMessages, setAiMessages] = useState([]);

  const month = new Date().getMonth() + 1;
  const year = new Date().getFullYear();

  useEffect(() => {
    // Fetch monthly summary
    fetchMonthlySummary(userId, month, year)
      .then(data => setSummary(data))
      .catch(err => console.error(err));

    // Fetch initial AI insight
    queryAI(userId, "Show me insights for this month")
      .then(data => {
        setAiMessages([{ sender: "AI", message: data?.response || "No insights" }]);
      })
      .catch(err => console.error(err));
  }, [userId]);

  const handleSendMessage = async (msg) => {
    setAiMessages(prev => [...prev, { sender: "User", message: msg }]);

    try {
      const res = await queryAI(userId, msg);
      setAiMessages(prev => [...prev, { sender: "AI", message: res?.response || "No response" }]);
    } catch (err) {
      setAiMessages(prev => [...prev, { sender: "AI", message: "Error getting response" }]);
    }
  };

  return (
    <div>
      <h2>Monthly Summary</h2>
      {summary ? (
        <div>
          <p>Total Spending: ${summary.total_expense}</p>
          <ul>
            {Object.entries(summary.by_category).map(([cat, val]) => (
              <li key={cat}>{cat}: ${val}</li>
            ))}
          </ul>
        </div>
      ) : (
        <p>Loading summary...</p>
      )}

      <h2>AI Chat</h2>
      <Chat messages={aiMessages} onSend={handleSendMessage} />
    </div>
  );
}

export default Home;