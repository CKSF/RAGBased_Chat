import React, { useState, useEffect, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import mermaid from "mermaid";
import { clsx } from "clsx";
import {
  Bot,
  User,
  ChevronDown,
  ChevronRight,
  BrainCircuit,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { ChatMessage } from "@/lib/api";

// ----------------------------------------------------------------------
// 1. Mermaid Initialization
// ----------------------------------------------------------------------
mermaid.initialize({
  startOnLoad: false,
  theme: "neutral",
  securityLevel: "loose",
  fontFamily:
    "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
});

// ----------------------------------------------------------------------
// 2. Safe Preprocessing
// ----------------------------------------------------------------------
const preprocessContent = (text: string | undefined) => {
  if (!text) return "";
  // Removes ```markdown wrappers from lists so they render as HTML
  return text.replace(/```(?:markdown|text)\n([\s\S]*?)\n```/g, "$1");
};

// ----------------------------------------------------------------------
// 3. Sub-component: Mermaid Diagram
// ----------------------------------------------------------------------
const MermaidDiagram = ({ content }: { content: string }) => {
  const [svg, setSvg] = useState<string>("");
  const [error, setError] = useState<boolean>(false);
  const id = useMemo(
    () => `mermaid-${Math.random().toString(36).slice(2)}`,
    []
  );

  useEffect(() => {
    let mounted = true;
    const renderChart = async () => {
      const cleanContent = content
        .replace(/```mermaid/g, "")
        .replace(/```/g, "")
        .trim();

      if (!cleanContent) return;

      try {
        const { svg: renderedSvg } = await mermaid.render(id, cleanContent);
        if (mounted) {
          setSvg(renderedSvg);
          setError(false);
        }
      } catch (err) {
        if (mounted) setError(true);
      }
    };

    const timer = setTimeout(renderChart, 100);
    return () => {
      mounted = false;
      clearTimeout(timer);
    };
  }, [content, id]);

  if (error) {
    return (
      <div className="my-4 p-4 border border-red-200 bg-red-50 rounded text-red-600 text-xs font-mono">
        <div className="flex items-center gap-2 mb-2 font-bold">
          <AlertCircle className="w-4 h-4" />
          <span>Diagram Render Failed</span>
        </div>
        <pre className="whitespace-pre-wrap">{content}</pre>
      </div>
    );
  }

  return svg ? (
    <div className="my-6 flex justify-center bg-white dark:bg-zinc-950 p-4 rounded-lg border border-zinc-200 dark:border-zinc-800 shadow-sm overflow-x-auto">
      <div dangerouslySetInnerHTML={{ __html: svg }} />
    </div>
  ) : (
    <div className="flex items-center justify-center py-8 text-zinc-400 gap-2">
      <Loader2 className="w-4 h-4 animate-spin" />
      <span className="text-xs">Generating Diagram...</span>
    </div>
  );
};

// ----------------------------------------------------------------------
// 4. Main Component
// ----------------------------------------------------------------------
export function MessageBubble({
  role,
  content,
  sources,
  thoughts,
  timestamp,
}: ChatMessage) {
  const isUser = role === "user";
  const [isThinkingOpen, setIsThinkingOpen] = useState(true);

  const displayContent = useMemo(() => preprocessContent(content), [content]);

  const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";

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

      <div className="flex-1 space-y-2 overflow-hidden">
        {/* Thoughts Section */}
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
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeRaw]}
            components={{
              // FIXED: Added 'any' type to 'props' to fix the TS error
              code: (props: any) => {
                const { inline, className, children } = props;
                const match = /language-(\w+)/.exec(className || "");
                const lang = match ? match[1] : "";
                const codeString = String(children).replace(/\n$/, "");

                // 1. Detect Mermaid
                const isMermaid =
                  lang === "mermaid" ||
                  (!inline &&
                    /^\s*(graph|flowchart|pie|sequenceDiagram|classDiagram|stateDiagram|erDiagram|gantt|journey|gitGraph)/.test(
                      codeString
                    ));

                if (!inline && isMermaid) {
                  return <MermaidDiagram content={codeString} />;
                }

                // 2. Default Code Block
                return (
                  <code className={className} {...props}>
                    {children}
                  </code>
                );
              },
            }}
          >
            {displayContent}
          </ReactMarkdown>

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
                <a
                  key={i}
                  href={`${API_BASE_URL}/api/source/${encodeURIComponent(
                    source
                  )}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-2 py-1 text-xs bg-blue-50 text-blue-600 rounded-md border border-blue-100 dark:bg-blue-900/20 dark:text-blue-300 dark:border-blue-800 hover:underline cursor-pointer transition-colors"
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
