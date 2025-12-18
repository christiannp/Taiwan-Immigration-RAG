import React from "react";
import { Tooltip } from "@shadcn/ui"; // assume a tooltip component

interface ChatMessage {
  role: "user" | "assistant" | "status";
  content: string;
}

interface ChatProps {
  messages: ChatMessage[];
}

export function Chat({ messages }: ChatProps) {
  return (
    <div className="space-y-4">
      {messages.map((msg, idx) => (
        <div key={idx} className={`${msg.role === "user" ? "text-right" : "text-left"}`}>
          {msg.role === "status" ? (
            <div className="italic text-gray-500">{msg.content}</div>
          ) : (
            <div>
              {msg.content.split(/(\[\d+\])/).map((chunk, i) => {
                const match = chunk.match(/^\[(\d+)\]$/);
                if (match) {
                  const num = match[1];
                  return (
                    <Tooltip key={i} content={`Source ${num} (click to view URL)`}>
                      <span className="text-blue-500 cursor-pointer hover:underline">[{num}]</span>
                    </Tooltip>
                  );
                } else {
                  return <span key={i}>{chunk}</span>;
                }
              })}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}