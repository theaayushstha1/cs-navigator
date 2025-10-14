// src/Chat.jsx
import { useState, useEffect } from "react";

export default function Chat() {
  const [messages, setMessages] = useState([]);  // { from: "user"|"bot", text }
  const [input, setInput] = useState("");
  const token = localStorage.getItem("token");

  useEffect(() => {
    if (!token) {
      alert("Please log in first");
    }
  }, [token]);

  async function sendMessage(e) {
    e.preventDefault();
    if (!input.trim()) return;
    setMessages(msgs => [...msgs, { from: "user", text: input }]);
    const query = input;
    setInput("");

    const res = await fetch("/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({ query })
    });

    if (res.ok) {
      const { response } = await res.json();
      setMessages(msgs => [...msgs, { from: "bot", text: response }]);
    } else if (res.status === 403) {
      alert("Your session expired—please log in again.");
      localStorage.removeItem("token");
      window.location.reload();
    } else {
      const { detail } = await res.json();
      setMessages(msgs => [...msgs, { from: "bot", text: `Error: ${detail}` }]);
    }
  }

  return (
    <div>
      <div style={{ maxHeight: 400, overflowY: "auto" }}>
        {messages.map((m, i) => (
          <div key={i} style={{ textAlign: m.from === "user" ? "right" : "left" }}>
            <b>{m.from === "user" ? "You:" : "Bot:"}</b> {m.text}
          </div>
        ))}
      </div>
      <form onSubmit={sendMessage}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Type your question..."
        />
        <button type="submit">Send</button>
      </form>
    </div>
  );
}
