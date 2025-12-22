import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import rehypeRaw from "rehype-raw";
import { clsx } from "clsx";
import {
  Bot,
  User,
  ChevronDown,
  ChevronRight,
  BrainCircuit,
} from "lucide-react";
import { ChatMessage } from "@/lib/api";

// 🔧 SPECIALIZED PRE-PROCESSOR FOR TEXT/SIZHENG CONTENT
const preprocessContent = (content: string) => {
  if (!content) return "";

  return (
    content
      // 1. Fix broken headers/lists (missing newlines)
      .replace(/([^\n])\n(#{1,6}\s|[-*]\s|\d+\.\s)/g, "$1\n\n$2")

      // 2. 🚫 PREVENT BLACK BOXES: Remove 4-space indents
      // If the LLM tries to indent a paragraph, we flatten it to normal text
      .replace(/^ {4,}/gm, "")
      .replace(/\n {4,}/g, "\n")
  );
};

export function MessageBubble({
  role,
  content,
  sources,
  thoughts,
  timestamp,
}: ChatMessage) {
  const isUser = role === "user";
  const [isThinkingOpen, setIsThinkingOpen] = useState(true);

  // Format time (e.g., "14:30")
  const timeString = timestamp
    ? new Date(timestamp).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      })
    : "";

  return (
    <div
      className={clsx(
        "flex w-full gap-4 p-4",
        isUser ? "bg-white dark:bg-zinc-900" : "bg-zinc-50 dark:bg-zinc-800/50"
      )}
    >
      {/* Avatar Section */}
      <div className={clsx("flex flex-col items-center gap-1 shrink-0")}>
        <div
          className={clsx(
            "flex h-8 w-8 select-none items-center justify-center rounded-md border shadow-sm",
            isUser
              ? "bg-white dark:bg-zinc-950"
              : "bg-black text-white dark:bg-white dark:text-black"
          )}
        >
          {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
        </div>
        {timeString && (
          <span className="text-[10px] text-zinc-400 font-medium">
            {timeString}
          </span>
        )}
      </div>

      <div className="flex-1 space-y-2 overflow-hidden min-w-0">
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
        <div className="prose break-words dark:prose-invert prose-p:leading-relaxed prose-pre:p-0 text-sm md:text-base max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm, remarkBreaks]}
            rehypePlugins={[rehypeRaw]}
            components={{
              // Overwrite default Code Block rendering to look like a Quote/Box
              // instead of a black terminal window.
              code({ node, inline, className, children, ...props }: any) {
                return inline ? (
                  // Inline code (like specific terms)
                  <code
                    {...props}
                    className="bg-zinc-100 dark:bg-zinc-800 px-1.5 py-0.5 rounded-md font-bold text-zinc-700 dark:text-zinc-300"
                  >
                    {children}
                  </code>
                ) : (
                  // Block code (Fallback for accidental code blocks)
                  // Render as a soft gray box with wrapped text, not a black terminal
                  <div className="bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200 dark:border-zinc-700 rounded-lg p-4 my-4 text-zinc-600 dark:text-zinc-300 overflow-x-auto whitespace-pre-wrap font-sans text-sm">
                    {children}
                  </div>
                );
              },
            }}
          >
            {preprocessContent(content)}
          </ReactMarkdown>

          {/* Cursor */}
          {role === "assistant" && !content && (
            <span className="inline-block w-2 h-4 bg-zinc-400 animate-pulse align-middle ml-1" />
          )}
        </div>

        {/* Sources Footer */}
        {sources && sources.length > 0 && (
          <div className="mt-4 pt-3 border-t border-zinc-200 dark:border-zinc-700/50">
            <p className="text-xs font-semibold text-zinc-500 mb-2">
              📚 参考文献:
            </p>
            <div className="flex flex-wrap gap-2">
              {sources.map((source, i) => (
                <a
                  key={i}
                  href={`http://localhost:5000/api/source/${encodeURIComponent(
                    source
                  )}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-2 py-1 text-xs bg-red-50 text-red-700 rounded-md border border-red-100 dark:bg-red-900/20 dark:text-red-300 dark:border-red-900/50 hover:underline cursor-pointer transition-colors"
                >
                  {source}
                </a>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
