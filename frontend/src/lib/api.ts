export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: string[];
  thoughts?: string[];
  timestamp?: string;
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

// ✅ Fix: Return explicit Record type
const getAuthHeader = (): Record<string, string> => {
  if (typeof window !== "undefined") {
    const pwd = localStorage.getItem("app_password");
    if (pwd) {
      return { "X-Access-Token": pwd };
    }
  }
  return {};
};

export const api = {
  async sendMessage(message: string, history: ChatMessage[] = []) {
    const res = await fetch("http://localhost:5001/api/chat/send", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeader()
      },
      body: JSON.stringify({ message, history }),
    });
    if (!res.ok) {
      let errorText = await res.text().catch(() => "No error details");
      try {
        const json = JSON.parse(errorText);
        if (json.error) errorText = json.error;
      } catch { }
      throw new Error(`API Error ${res.status}: ${errorText}`);
    }
    return res.json() as Promise<ChatResponse>;
  },

  async generateLessonPlan(topic: string, grade: string) {
    const res = await fetch("http://localhost:5001/api/lesson/generate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeader()
      },
      body: JSON.stringify({ topic, grade }),
    });
    if (!res.ok) {
      let errorText = await res.text().catch(() => "No error details");
      try {
        const json = JSON.parse(errorText);
        if (json.error) errorText = json.error;
      } catch { }
      throw new Error(`API Error ${res.status}: ${errorText}`);
    }
    return res.json() as Promise<LessonResponse>;
  },

  // ✅ Streaming Chat
  async streamMessage(
    message: string,
    history: ChatMessage[],
    onUpdate: (chunk: Partial<ChatMessage>) => void
  ) {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...getAuthHeader()
    };

    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:5001/api"
      }/chat/send`,
      {
        method: "POST",
        headers, // ✅ Pass as strictly typed object
        body: JSON.stringify({ message, history }),
      }
    );

    if (!response.body) throw new Error("No response body");
    if (!response.ok) {
      if (response.status === 401) throw new Error("Unauthorized");
      throw new Error("Network response was not ok");
    }

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
              onUpdate({ thoughts: [event.data] });
            } else if (event.type === "token") {
              onUpdate({ content: event.data });
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

  // ✅ Streaming Lesson Plan
  async streamLessonPlan(
    topic: string,
    grade: string,
    onUpdate: (chunk: Partial<ChatMessage>) => void
  ) {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...getAuthHeader()
    };

    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:5001/api"
      }/lesson/generate`,
      {
        method: "POST",
        headers, // ✅ Pass as strictly typed object
        body: JSON.stringify({ topic, grade }),
      }
    );

    if (!response.body) throw new Error("No response body");
    if (!response.ok) {
      if (response.status === 401) throw new Error("Unauthorized");
      throw new Error("Network response was not ok");
    }

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
              onUpdate({ thoughts: [event.data] });
            } else if (event.type === "token") {
              onUpdate({ content: event.data });
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
