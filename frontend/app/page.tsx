"use client";

import { useChat } from "@ai-sdk/react";
import { useState } from "react";
import ChatInput from "../components/chat";  // import the Chat component

export default function Page() {
  const { messages, sendMessage } = useChat();
  const [input, setInput] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage({ content: input });
    setInput("");
  };

  return (
    <main className="flex flex-col items-center justify-start p-4">
      <div className="w-full max-w-md">
        {/* Chat history */}
        {messages.map(msg => (
          <div key={msg.id} className={`my-2 p-2 rounded ${msg.role === 'user' ? 'bg-blue-100 text-right' : 'bg-gray-100'}`}>
            {msg.parts.map((part, i) => (
              <span key={i}>
                {part.type === "text" ? part.text : part.type === "status" ? (
                  <em>⋯{part.content}⋯</em>
                ) : null}
              </span>
            ))}
          </div>
        ))}
        {/* Input form */}
        <form onSubmit={handleSubmit} className="fixed bottom-4 w-full max-w-md flex">
          <input
            className="flex-grow p-2 border rounded"
            value={input}
            placeholder="Type your message..."
            onChange={e => setInput(e.currentTarget.value)}
          />
          <button type="submit" className="ml-2 px-4 py-2 bg-blue-500 text-white rounded">Send</button>
        </form>
      </div>
    </main>
  );
}