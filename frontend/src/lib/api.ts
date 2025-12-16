export interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
    sources?: string[];
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

export const api = {
    async sendMessage(message: string, history: ChatMessage[] = []) {
        // Convert history to format expected by backend if needed, 
        // but for now backend accepts list of dicts which matches.
        const res = await fetch('http://localhost:5000/api/chat/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, history }),
        });
        if (!res.ok) {
            let errorText = await res.text().catch(() => 'No error details');
            try {
                // Try to parse JSON if possible to look for "error" field
                const json = JSON.parse(errorText);
                if (json.error) errorText = json.error;
            } catch { }
            throw new Error(`API Error ${res.status}: ${errorText}`);
        }
        return res.json() as Promise<ChatResponse>;
    },

    async generateLessonPlan(topic: string, grade: string) {
        const res = await fetch('http://localhost:5000/api/lesson/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic, grade }),
        });
        if (!res.ok) {
            let errorText = await res.text().catch(() => 'No error details');
            try {
                const json = JSON.parse(errorText);
                if (json.error) errorText = json.error;
            } catch { }
            throw new Error(`API Error ${res.status}: ${errorText}`);
        }
        return res.json() as Promise<LessonResponse>;
    },
};
