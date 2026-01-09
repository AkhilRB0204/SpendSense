import { useState } from "react"; 
import { queryAI } from "./services/api";

export default function Chat() {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");

    const handleSend = async () => {
        if (!input.trim()) return;

        const newMessage = { sender: "user", text: input };
        setMessages([...messages, newMessage]);

        try {
            const res = await queryAI(currentUser.user_id, input);
            const aiMessage = {
                sender: "ai",
                text: res.response || "Sorry, I didn't understand that."
                };
                setMessages(prev => [...prev, aiMessage]);
                } catch (err) {
                    setMessages(prev => [
                        ...prev,
                        { sender: "ai", text: "Error connecting to AI service." }
                    ]);
                    }
         setInput("");
    }; 

    const handleKeyPress = (e) => {
        if (e.key === "Enter") handleSend();
    };

    return (
    <div className="chat-container">
      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`chat-message ${msg.sender === "user" ? "user" : "ai"}`}
          >
            {msg.text}
          </div>
        ))}
      </div>
      <div className="chat-input">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your message..."
        />
        <button onClick={handleSend}>Send</button>
      </div>
    </div>
  );

}