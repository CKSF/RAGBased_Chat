import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import { clsx } from "clsx";
import {
  Bot,
  User,
  ChevronDown,
  ChevronRight,
  BrainCircuit,
} from "lucide-react";
import { ChatMessage } from "@/lib/api"; // Import your type

export function MessageBubble({
  role,
  content,
  sources,
  thoughts,
}: ChatMessage) {
  const isUser = role === "user";
  const [isThinkingOpen, setIsThinkingOpen] = useState(true); // Default open or closed

  return (
    <div
      className={clsx(
        "flex w-full gap-4 p-4",
        isUser ? "bg-white dark:bg-zinc-900" : "bg-zinc-50 dark:bg-zinc-800/50"
      )}
    >
      <div
        className={clsx(
          "flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-md border shadow-sm",
          isUser
            ? "bg-white dark:bg-zinc-950"
            : "bg-black text-white dark:bg-white dark:text-black"
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      <div className="flex-1 space-y-2 overflow-hidden">
        {/* 🧠 Collapsible Thoughts Section */}
        {!isUser && thoughts && thoughts.length > 0 && (
          <div className="mb-4 rounded-lg border border-zinc-200 bg-zinc-100/50 dark:border-zinc-700 dark:bg-zinc-900/50 overflow-hidden">
            <button
              onClick={() => setIsThinkingOpen(!isThinkingOpen)}
              className="flex items-center gap-2 w-full p-2 text-xs font-medium text-zinc-500 hover:bg-zinc-200/50 dark:hover:bg-zinc-800 transition-colors"
            >
              <BrainCircuit className="w-3.5 h-3.5" />
              <span>思考过程 ({thoughts.length} 步)</span>
              {isThinkingOpen ? (
                <ChevronDown className="w-3 h-3 ml-auto" />
              ) : (
                <ChevronRight className="w-3 h-3 ml-auto" />
              )}
            </button>

            {isThinkingOpen && (
              <div className="p-3 pt-0 space-y-1">
                {thoughts.map((step, i) => (
                  <div
                    key={i}
                    className="flex gap-2 text-xs text-zinc-600 dark:text-zinc-400 font-mono animate-in fade-in slide-in-from-top-1 duration-300"
                  >
                    <span className="text-zinc-400 select-none">›</span>
                    <span>{step}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Main Content */}
        <div className="prose break-words dark:prose-invert prose-p:leading-relaxed prose-pre:p-0 text-sm md:text-base">
          <ReactMarkdown>{content}</ReactMarkdown>
          {/* Blinking cursor effect while generating */}
          {role === "assistant" && !content && (
            <span className="inline-block w-2 h-4 bg-zinc-400 animate-pulse align-middle ml-1" />
          )}
        </div>

        {/* Sources Footer */}
        {sources && sources.length > 0 && (
          <div className="mt-4 pt-3 border-t border-zinc-200 dark:border-zinc-700/50">
            <p className="text-xs font-semibold text-zinc-500 mb-2">
              📚 参考资料:
            </p>
            <div className="flex flex-wrap gap-2">
              {sources.map((source, i) => (
                <span
                  key={i}
                  className="px-2 py-1 text-xs bg-blue-50 text-blue-600 rounded-md border border-blue-100 dark:bg-blue-900/20 dark:text-blue-300 dark:border-blue-800"
                >
                  {source}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
