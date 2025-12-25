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

        {/* Rich Sources Footer (Evidence Cards) - Grouped by Source */}
        {sources && sources.length > 0 && (() => {
          // GROUPING LOGIC: Group sources by filename (source property)
          const groupedSources: Record<string, { pages: Set<string | number>, grade?: string }> = {};

          sources.forEach(s => {
            if (typeof s === 'string') {
              // Backward compatibility for old string sources
              if (!groupedSources[s]) groupedSources[s] = { pages: new Set() };
            } else {
              if (!groupedSources[s.source]) groupedSources[s.source] = { pages: new Set(), grade: s.grade };
              if (s.page) groupedSources[s.source].pages.add(s.page);
            }
          });

          return (
            <div className="mt-4 pt-4 border-t border-zinc-200 dark:border-zinc-700/50">
              <p className="text-xs font-semibold text-zinc-500 mb-3 flex items-center gap-2">
                <span className="bg-blue-100 text-blue-600 p-1 rounded">📚</span>
                参考资料与证据链 (Evidence Chain):
              </p>
              <div className="grid grid-cols-1 gap-2">
                {Object.entries(groupedSources).map(([sourceName, data], i) => (
                  <div
                    key={i}
                    className="group relative flex flex-col items-start p-3 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg hover:border-blue-300 dark:hover:border-blue-700 transition-colors"
                  >
                    {/* Header: Source Name Only */}
                    <div className="flex flex-wrap items-center gap-2 w-full">
                      {/* Index Badge */}
                      <span className="flex items-center justify-center w-5 h-5 rounded-full bg-blue-100 text-blue-600 text-[10px] font-bold shrink-0">
                        {i + 1}
                      </span>

                      {/* Filename */}
                      <span className="text-sm font-medium text-zinc-700 dark:text-zinc-200 truncate flex-1 min-w-[150px]">
                        {sourceName}
                      </span>
                    </div>

                    {/* Link to Source File */}
                    <a
                      href={`${API_BASE_URL}/api/source/${encodeURIComponent(sourceName)}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="absolute inset-0 rounded-lg focus:ring-2 focus:ring-blue-500"
                      aria-label={`View source ${sourceName}`}
                    />
                  </div>
                ))}
              </div>
            </div>
          );
        })()}
      </div>
    </div>
  );
}
