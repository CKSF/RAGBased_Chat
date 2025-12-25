"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, Sparkles, BookOpen, Loader2 } from "lucide-react";
import { clsx } from "clsx";
import { api, ChatMessage } from "@/lib/api";
import { MessageBubble } from "@/components/message-bubble";

type Mode = "chat" | "lesson";

const GRADES = ["通用", "小学", "初中", "高中", "大学", "硕士", "博士"];

export function ChatInterface() {
  const [mode, setMode] = useState<Mode>("chat");
  const [histories, setHistories] = useState<Record<Mode, ChatMessage[]>>({
    chat: [],
    lesson: [],
  });

  // Derived state for current view
  const messages = histories[mode];

  // Independent Loading States
  const [loadingStates, setLoadingStates] = useState<Record<Mode, boolean>>({
    chat: false,
    lesson: false,
  });

  // Independent Inputs
  const [inputs, setInputs] = useState<Record<Mode, string>>({
    chat: "",
    lesson: "",
  });

  // Independent Grades
  const [grades, setGrades] = useState<Record<Mode, string>>({
    chat: "通用",
    lesson: "通用",
  });

  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, mode]); // Trigger scroll on message add OR mode switch

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    const currentMode = mode; // Capture mode for closure
    const currentInput = inputs[currentMode];

    if (!currentInput.trim() || loadingStates[currentMode]) return;

    const userMsg = currentInput.trim();

    // Clear Input for THIS mode
    setInputs((prev) => ({ ...prev, [currentMode]: "" }));

    // Set Loading for THIS mode
    setLoadingStates((prev) => ({ ...prev, [currentMode]: true }));

    // 1. Add User Message & Assistant Placeholder atomically
    const userMessage: ChatMessage = {
      role: "user",
      content: userMsg,
      timestamp: new Date().toISOString(),
    };

    setHistories((prev) => ({
      ...prev,
      [currentMode]: [
        ...prev[currentMode],
        userMessage,
        {
          role: "assistant",
          content: "",
          thoughts: [],
          timestamp: new Date().toISOString(),
        } as ChatMessage,
      ],
    }));


    // Helper to update the last message state OF THE CURRENT MODE
    const updateLastMessage = (chunk: Partial<ChatMessage>) => {
      setHistories((prev) => {
        const currentList = prev[currentMode];
        if (currentList.length === 0) return prev; // Should not happen

        const last = currentList[currentList.length - 1];
        const others = currentList.slice(0, -1);

        // Merge thoughts (append to array)
        const newThoughts = chunk.thoughts
          ? [...(last.thoughts || []), ...chunk.thoughts]
          : last.thoughts;

        // Merge content (string append)
        const newContent = chunk.content
          ? last.content + chunk.content
          : last.content;

        const updatedLast = {
          ...last,
          content: newContent,
          thoughts: newThoughts,
          sources: chunk.sources || last.sources,
        };

        return {
          ...prev,
          [currentMode]: [...others, updatedLast],
        };
      });
    };

    try {
      const currentGrade = grades[currentMode];

      if (currentMode === "chat") {
        // CHAT STREAMING
        // Note: We use the *updated* history logic. 
        // Ideally we pass the history *including* the new user message.
        // But since state might not update immediately, we construct the 'sent' history manually.
        // However, `messages` in component scope is old. 
        // We need to pass the history intended for the backend.
        const historyForBackend = [...histories['chat'], userMessage];

        await api.streamMessage(userMsg, historyForBackend, currentGrade, updateLastMessage);
      } else {
        // LESSON STREAMING
        // Pass the grade state here
        await api.streamLessonPlan(userMsg, currentGrade, updateLastMessage);
      }
    } catch (error) {
      console.error(error);
      setHistories((prev) => {
        const currentList = prev[currentMode];
        const last = currentList[currentList.length - 1];
        const others = currentList.slice(0, -1);

        return {
          ...prev,
          [currentMode]: [...others, { ...last, content: last.content + `\n\n❌ Error: ${error}` }],
        };
      });
    } finally {
      setLoadingStates((prev) => ({ ...prev, [currentMode]: false }));
    }
  };

  return (
    <div className="flex flex-col h-[85vh] w-full max-w-4xl mx-auto bg-white dark:bg-zinc-900 shadow-xl rounded-xl overflow-hidden border border-zinc-200 dark:border-zinc-800">
      {/* Header logic remains the same... */}
      <div className="border-b border-zinc-200 dark:border-zinc-800 p-4 bg-white/80 dark:bg-zinc-900/80 backdrop-blur-md sticky top-0 z-10">
        <div className="relative flex p-1 bg-zinc-100 dark:bg-zinc-800 rounded-lg max-w-[320px] mx-auto">
          <button
            onClick={() => setMode("chat")}
            className={clsx(
              "flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-md text-sm font-medium transition-all duration-200 ease-in-out",
              mode === "chat"
                ? "bg-white dark:bg-zinc-700 text-zinc-900 dark:text-white shadow-sm ring-1 ring-black/5"
                : "text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200 hover:bg-zinc-50/50 dark:hover:bg-zinc-700/50"
            )}
          >
            <Sparkles
              className={clsx(
                "w-4 h-4",
                mode === "chat" ? "text-blue-500" : "text-zinc-400"
              )}
            />
            智能答疑
          </button>
          <button
            onClick={() => setMode("lesson")}
            className={clsx(
              "flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-md text-sm font-medium transition-all duration-200 ease-in-out",
              mode === "lesson"
                ? "bg-white dark:bg-zinc-700 text-zinc-900 dark:text-white shadow-sm ring-1 ring-black/5"
                : "text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200 hover:bg-zinc-50/50 dark:hover:bg-zinc-700/50"
            )}
          >
            <BookOpen
              className={clsx(
                "w-4 h-4",
                mode === "lesson" ? "text-purple-500" : "text-zinc-400"
              )}
            />
            教案生成
          </button>
        </div>
      </div>

      {/* Messages Area... */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-zinc-400 space-y-4">
            {/* ... icons ... */}
            <p className="text-lg font-medium">
              {mode === "chat"
                ? "有什么思政问题可以帮你的吗？"
                : "请输入主题生成教案"}
            </p>
          </div>
        )}
        {messages.map((msg, idx) => (
          <MessageBubble key={idx} {...msg} />
        ))}
        {loadingStates[mode] && (
          <div className="flex items-center gap-2 text-zinc-500 p-4">
            <Loader2 className="w-5 h-5 animate-spin" />
            <span className="text-sm">正在思考中...</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 bg-white dark:bg-zinc-900 border-t border-zinc-200 dark:border-zinc-800">
        <form
          onSubmit={handleSubmit}
          className="relative flex gap-3 max-w-3xl mx-auto"
        >
          {/* UPDATE: Grade Selector is now ALWAYS visible (or based on your preference) */}
          <select
            value={grades[mode]}
            onChange={(e) => setGrades(prev => ({ ...prev, [mode]: e.target.value }))}
            className="h-12 px-3 rounded-lg border border-zinc-200 bg-zinc-50 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-zinc-800 dark:border-zinc-700"
          >
            {GRADES.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </select>

          <input
            type="text"
            value={inputs[mode]}
            onChange={(e) => setInputs(prev => ({ ...prev, [mode]: e.target.value }))}
            placeholder={
              mode === "chat"
                ? "输入问题... (例：何为高质量发展)"
                : "输入课程主题..."
            }
            className="flex-1 h-12 px-4 rounded-lg border border-zinc-200 bg-zinc-50 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-zinc-800 dark:border-zinc-700"
          />

          <button
            type="submit"
            disabled={!inputs[mode].trim() || loadingStates[mode]}
            className="h-12 px-6 rounded-lg bg-black text-white font-medium hover:bg-zinc-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors dark:bg-white dark:text-black dark:hover:bg-zinc-200 flex items-center gap-2"
          >
            <Send className="w-4 h-4" />
            {loadingStates[mode] ? "生成中" : "发送"}
          </button>
        </form>
        {/* Footer text... */}
      </div>
    </div>
  );
}
