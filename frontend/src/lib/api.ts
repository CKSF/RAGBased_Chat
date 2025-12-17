export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: string[];
  thoughts?: string[];
}

export interface ChatResponse {
  reply: string;
  sources: string[];
  context_used?: string;
}

export interface LessonResponse {
  lesson_plan: string;
  sources: string[];
}

const getAuthHeader = (): Record<string, string> => {
  if (typeof window !== "undefined") {
    return { "X-Access-Token": localStorage.getItem("app_password") || "" };
  }
  return {};
};

const isProd = process.env.NODE_ENV === "production";
const API_BASE = isProd ? "" : "http://localhost:5001";

export const api = {
  async sendMessage(message: string, history: ChatMessage[] = []) {
    // Convert history to format expected by backend if needed,
    // but for now backend accepts list of dicts which matches.
    const res = await fetch(`${API_BASE}/api/chat/send`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeader() },
      body: JSON.stringify({ message, history }),
    });
    if (!res.ok) {
      let errorText = await res.text().catch(() => "No error details");
      try {
        // Try to parse JSON if possible to look for "error" field
        const json = JSON.parse(errorText);
        if (json.error) errorText = json.error;
      } catch {}
      throw new Error(`API Error ${res.status}: ${errorText}`);
    }
    return res.json() as Promise<ChatResponse>;
  },

  async streamMessage(
    message: string,
    history: ChatMessage[],
    onUpdate: (chunk: Partial<ChatMessage>) => void
  ) {
    const response = await fetch(`${API_BASE}/api/chat/send`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeader() },
      body: JSON.stringify({ message, history }),
    });

    if (!response.body) throw new Error("No response body");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");
      buffer = lines.pop() || ""; // Keep incomplete chunk in buffer

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const jsonStr = line.slice(6);
          try {
            const event = JSON.parse(jsonStr);

            if (event.type === "thought") {
              // Update UI with new thought step
              onUpdate({ thoughts: [event.data] });
            } else if (event.type === "token") {
              // Append token to content
              onUpdate({ content: event.data });
            } else if (event.type === "done") {
              // Finalize sources
              onUpdate({ sources: event.data.sources });
            } else if (event.type === "error") {
              throw new Error(event.data);
            }
          } catch (e) {
            console.error("Error parsing SSE:", e);
          }
        }
      }
    }
  },

  async streamLessonPlan(
    topic: string,
    grade: string,
    onUpdate: (chunk: Partial<ChatMessage>) => void
  ) {
    const response = await fetch(`${API_BASE}/api/lesson/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeader() },
      body: JSON.stringify({ topic, grade }),
    });

    if (!response.body) throw new Error("No response body");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const jsonStr = line.slice(6);
          try {
            const event = JSON.parse(jsonStr);

            if (event.type === "thought") {
              onUpdate({ thoughts: [event.data] }); // Append thought
            } else if (event.type === "token") {
              onUpdate({ content: event.data }); // Append token
            } else if (event.type === "done") {
              onUpdate({ sources: event.data.sources });
            } else if (event.type === "error") {
              throw new Error(event.data);
            }
          } catch (e) {
            console.error("Error parsing SSE:", e);
          }
        }
      }
    }
  },
};
