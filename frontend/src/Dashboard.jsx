import React from "react";
import Home from "./Home";

function Dashboard({ userId }) {
  return (
    <div style={{ padding: "20px" }}>
      <h1>SpendSense Dashboard</h1>
      <Home userId={userId} />
    </div>
  );
}

export default Dashboard;