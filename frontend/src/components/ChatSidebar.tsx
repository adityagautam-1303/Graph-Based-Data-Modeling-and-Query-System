import { useState, useRef, useEffect } from "react";
import { Send, Bot } from "lucide-react";
import type { GraphData, ChatMessage } from "../types";

const API_BASE = "/api";

interface ChatSidebarProps {
  onQueryResult: (nodeIds: string[]) => void;
  graphData: GraphData;
}

export default function ChatSidebar({ onQueryResult, graphData }: ChatSidebarProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: "Hi! I can help you analyze the Order to Cash process. Try asking about sales orders, deliveries, billing documents, or journal entries.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("Agent is awaiting instructions.");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const extractIds = (text: string, data: any[]): string[] => {
    const ids: string[] = [];
    const prefixes = ["SO-", "BD-", "D-", "JE-", "P-", "BP-", "PL-"];

    // Extract any word/number from text
    const words = text.match(/\b\w+\b/g) || [];

    // Extract everything straight out of the SQL data payload
    const dataValues = data.flat(Infinity).map(String);

    const candidates = [...words, ...dataValues];

    for (const val of candidates) {
      for (const p of prefixes) {
        const candidateId = p + val;
        // Check if this ID exists in the graph
        if (graphData.nodes.some((n) => n.id === candidateId)) {
          ids.push(candidateId);
          break;
        }
      }
    }
    return [...new Set(ids)];
  };

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = '44px'; // Reset to base height to measure correctly
      const scrollHeight = textareaRef.current.scrollHeight;
      textareaRef.current.style.height = `${Math.min(scrollHeight, 200)}px`;
    }
  }, [input]);

  const send = async () => {
    const q = input.trim();
    if (!q || loading) return;
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = '44px'; // Reset height after sending

    setMessages((m) => [...m, { role: "user", content: q }]);
    setLoading(true);
    setStatus("Agent is thinking...");

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: q,
          history: messages.slice(-6).map((x) => ({ role: x.role, content: x.content })),
        }),
      });
      const data = await res.json();
      const nodeIds = extractIds(data.answer, data.data || []);
      if (nodeIds.length > 0) onQueryResult(nodeIds);
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: data.answer,
          sql: data.sql,
          data: data.data,
        },
      ]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: "Sorry, I encountered an error. Please try again." },
      ]);
    } finally {
      setLoading(false);
      setStatus("Agent is awaiting instructions.");
    }
  };

  return (
    <div className="chat-sidebar">
      <div className="chat-header">
        <h2>Chat with Graph</h2>
        <p className="chat-context">Graph Visualization</p>
        <div className="agent-badge">
          <div className="agent-icon">
            <span>D</span>
          </div>
          <span>Graph Agent</span>
        </div>
      </div>
      <div className="chat-messages" ref={scrollRef}>
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            {msg.role === "assistant" && (
              <div className="msg-avatar">
                <Bot size={18} />
              </div>
            )}
            <div className="msg-content">
              <p>{msg.content}</p>
            </div>
          </div>
        ))}
        {loading && (
          <div className="message assistant">
            <div className="msg-avatar">
              <Bot size={18} />
            </div>
            <div className="msg-content typing">Thinking...</div>
          </div>
        )}
      </div>
      <div className="chat-input-area">
        <div className="status-bar">
          <span className="status-dot" />
          <span className="status-text">{status}</span>
        </div>
        <div className="input-wrapper">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), send())}
            placeholder="Analyze anything"
            rows={1}
            disabled={loading}
            style={{ resize: "none", minHeight: "44px", overflowY: "auto", maxHeight: "200px", padding: "10px" }}
          />
          <button
            type="button"
            className="send-btn"
            onClick={send}
            disabled={loading || !input.trim()}
          >
            <Send size={18} />
            <span>Send</span>
          </button>
        </div>
      </div>
    </div>
  );
}
