import React, { useEffect, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts";
import { fetchExpenseSummary, fetchMonthlyTrend, queryAI } from "./services/api";
import Chat from "./chat";

function Home({ userId }) {
  const [summary, setSummary] = useState(null);
  const [trendData, setTrendData] = useState([]);
  const [aiMessages, setAiMessages] = useState([]);

  const month = new Date().getMonth() + 1;
  const year = new Date().getFullYear();

  useEffect(() => {
    fetchExpenseSummary(month, year)
      .then(data => setSummary(data))
      .catch(err => console.error(err));

    fetchMonthlyTrend(6)
      .then(data => setTrendData(data.trend || []))
      .catch(err => console.error(err));

    queryAI("Show me insights for this month")
      .then(data => {
        setAiMessages([{ sender: "AI", message: data?.response || "No insights" }]);
      })
      .catch(err => console.error(err));
  }, [userId]);

  const handleSendMessage = async (msg) => {
    setAiMessages(prev => [...prev, { sender: "User", message: msg }]);

    try {
      const res = await queryAI(msg);
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
            {Object.entries(summary.by_category || {}).map(([cat, val]) => (
              <li key={cat}>{cat}: ${val}</li>
            ))}
          </ul>
        </div>
      ) : (
        <p>Loading summary...</p>
      )}

      <h2>Monthly Spending Trend</h2>
      {trendData.length > 0 ? (
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={trendData} margin={{ top: 8, right: 24, left: 0, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="label" tick={{ fontSize: 12 }} />
            <YAxis tickFormatter={(v) => `$${v}`} tick={{ fontSize: 12 }} />
            <Tooltip formatter={(v) => [`$${Number(v).toFixed(2)}`, "Spending"]} />
            <Line
              type="monotone"
              dataKey="total"
              stroke="#6366f1"
              strokeWidth={2}
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <p>Loading trend...</p>
      )}

      <h2>AI Chat</h2>
      <Chat messages={aiMessages} onSend={handleSendMessage} />
    </div>
  );
}

export default Home;
