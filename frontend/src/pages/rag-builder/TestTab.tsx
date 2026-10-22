import { FormEvent, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "../../lib/api";
import type { ChatResponse } from "../../lib/types";

interface Message {
  role: "user" | "assistant";
  text: string;
  sources?: string[];
}

export default function TestTab({ projectId }: { projectId: number }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");

  const ask = useMutation({
    mutationFn: (text: string) => api.post<ChatResponse>(`/api/projects/${projectId}/chat`, { text }),
    onSuccess: (data) => {
      setMessages((prev) => [...prev, { role: "assistant", text: data.response, sources: data.sources }]);
    },
    onError: (error: Error) => {
      setMessages((prev) => [...prev, { role: "assistant", text: `Error: ${error.message}` }]);
    },
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;
    setMessages((prev) => [...prev, { role: "user", text }]);
    setInput("");
    ask.mutate(text);
  }

  return (
    <div className="max-w-2xl">
      <div className="bg-white border rounded-lg p-4 h-96 overflow-y-auto space-y-3 mb-4">
        {messages.length === 0 && (
          <p className="text-slate-400 text-sm">Ask a question to test this project's RAG pipeline.</p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
            <div
              className={`inline-block px-3 py-2 rounded-lg max-w-[80%] text-sm ${
                m.role === "user" ? "bg-slate-900 text-white" : "bg-slate-100"
              }`}
            >
              {m.text}
            </div>
            {m.sources && m.sources.length > 0 && (
              <div className="text-xs text-slate-400 mt-1">Sources: {m.sources.join(", ")}</div>
            )}
          </div>
        ))}
        {ask.isPending && <p className="text-slate-400 text-sm">Thinking...</p>}
      </div>
      <form onSubmit={onSubmit} className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question..."
          className="flex-1 border rounded px-3 py-2"
        />
        <button type="submit" className="bg-slate-900 text-white rounded px-4 py-2">
          Send
        </button>
      </form>
    </div>
  );
}
