"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, Sparkles, BookOpen, Loader2 } from "lucide-react";
import { clsx } from "clsx";
import { api, ChatMessage } from "@/lib/api";
import { MessageBubble } from "@/components/message-bubble";

type Mode = "chat" | "lesson";

const GRADES = ["小学", "初中", "高中", "大学", "研究生"];

export function ChatInterface() {
    const [mode, setMode] = useState<Mode>("chat");
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [isLoading, setIsLoading] = useState(false);

    // Inputs
    const [input, setInput] = useState("");
    const [grade, setGrade] = useState("大学");

    const bottomRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const handleSubmit = async (e?: React.FormEvent) => {
        e?.preventDefault();
        if (!input.trim() || isLoading) return;

        const userMsg = input.trim();
        setInput("");
        setIsLoading(true);

        // Add user message to UI immediately
        const newHistory: ChatMessage[] = [
            ...messages,
            { role: 'user', content: userMsg }
        ];
        setMessages(newHistory);

        try {
            if (mode === "chat") {
                // Chat Mode
                const data = await api.sendMessage(userMsg, messages);
                setMessages(prev => [
                    ...prev,
                    { role: 'assistant', content: data.reply, sources: data.sources }
                ]);
            } else {
                // Lesson Plan Mode
                // For lesson plan, we show a 'system' style message or just the result.
                // Let's treat it as an assistant response.
                const data = await api.generateLessonPlan(userMsg, grade);
                setMessages(prev => [
                    ...prev,
                    { role: 'assistant', content: data.lesson_plan, sources: data.sources }
                ]);
            }
        } catch (error) {
            console.error(error);
            setMessages(prev => [
                ...prev,
                { role: 'assistant', content: `❌ 请求失败: ${error instanceof Error ? error.message : String(error)}` }
            ]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-full w-full max-w-4xl mx-auto bg-white dark:bg-zinc-900 shadow-xl rounded-xl overflow-hidden border border-zinc-200 dark:border-zinc-800">

            {/* Header / Mode Switcher */}
            <div className="border-b border-zinc-200 dark:border-zinc-800 p-4 bg-zinc-50/50 dark:bg-zinc-900/50 backdrop-blur-sm sticky top-0 z-10">
                <div className="flex items-center justify-center gap-2 max-w-sm mx-auto bg-zinc-100 dark:bg-zinc-800 p-1 rounded-full">
                    <button
                        onClick={() => setMode("chat")}
                        className={clsx(
                            "flex items-center gap-2 px-6 py-2 rounded-full text-sm font-medium transition-all",
                            mode === "chat"
                                ? "bg-white dark:bg-zinc-700 text-black dark:text-white shadow-sm"
                                : "text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
                        )}
                    >
                        <Sparkles className="w-4 h-4" />
                        智能答疑
                    </button>
                    <button
                        onClick={() => setMode("lesson")}
                        className={clsx(
                            "flex items-center gap-2 px-6 py-2 rounded-full text-sm font-medium transition-all",
                            mode === "lesson"
                                ? "bg-white dark:bg-zinc-700 text-black dark:text-white shadow-sm"
                                : "text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
                        )}
                    >
                        <BookOpen className="w-4 h-4" />
                        教案生成
                    </button>
                </div>
            </div>

            {/* Chat Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6">
                {messages.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full text-zinc-400 space-y-4">
                        <div className="p-4 bg-zinc-100 dark:bg-zinc-800 rounded-full">
                            {mode === 'chat' ? <Sparkles className="w-8 h-8" /> : <BookOpen className="w-8 h-8" />}
                        </div>
                        <p className="text-lg font-medium">
                            {mode === 'chat' ? "有什么可以帮你的吗？" : "请输入主题生成教案"}
                        </p>
                    </div>
                )}

                {messages.map((msg, idx) => (
                    <MessageBubble key={idx} {...msg} />
                ))}

                {isLoading && (
                    <div className="flex items-center gap-2 text-zinc-500 p-4">
                        <Loader2 className="w-5 h-5 animate-spin" />
                        <span className="text-sm">正在思考中...</span>
                    </div>
                )}
                <div ref={bottomRef} />
            </div>

            {/* Input Area */}
            <div className="p-4 bg-white dark:bg-zinc-900 border-t border-zinc-200 dark:border-zinc-800">
                <form onSubmit={handleSubmit} className="relative flex gap-3 max-w-3xl mx-auto">

                    {/* Grade Selector (Only in Lesson Mode) */}
                    {mode === "lesson" && (
                        <select
                            value={grade}
                            onChange={(e) => setGrade(e.target.value)}
                            className="h-12 px-3 rounded-lg border border-zinc-200 bg-zinc-50 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-zinc-800 dark:border-zinc-700"
                        >
                            {GRADES.map(g => <option key={g} value={g}>{g}</option>)}
                        </select>
                    )}

                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder={mode === "chat" ? "输入问题... (Shift+Enter换行)" : "输入课程主题 (例如: 高质量发展)..."}
                        className="flex-1 h-12 px-4 rounded-lg border border-zinc-200 bg-zinc-50 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-zinc-800 dark:border-zinc-700"
                    />

                    <button
                        type="submit"
                        disabled={!input.trim() || isLoading}
                        className="h-12 px-6 rounded-lg bg-black text-white font-medium hover:bg-zinc-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors dark:bg-white dark:text-black dark:hover:bg-zinc-200 flex items-center gap-2"
                    >
                        <Send className="w-4 h-4" />
                        {isLoading ? "生成中" : "发送"}
                    </button>
                </form>
                <p className="text-center text-xs text-zinc-400 mt-2">
                    {mode === "chat"
                        ? "AI 基于 RAG 知识库回答，可能存在误差。"
                        : "教案由大模型生成，建议人工审核后使用。"}
                </p>
            </div>
        </div>
    );
}
