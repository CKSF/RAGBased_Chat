import React from 'react';
import ReactMarkdown from 'react-markdown';
import { clsx } from 'clsx';
import { Bot, User } from 'lucide-react';

interface MessageBubbleProps {
    role: 'user' | 'assistant';
    content: string;
    sources?: string[];
}

export function MessageBubble({ role, content, sources }: MessageBubbleProps) {
    const isUser = role === 'user';

    return (
        <div className={clsx("flex w-full gap-4 p-4", isUser ? "bg-white dark:bg-zinc-900" : "bg-zinc-50 dark:bg-zinc-800/50")}>
            <div className={clsx(
                "flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-md border shadow-sm",
                isUser ? "bg-white dark:bg-zinc-950" : "bg-black text-white dark:bg-white dark:text-black"
            )}>
                {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
            </div>

            <div className="flex-1 space-y-2 overflow-hidden">
                <div className="prose break-words dark:prose-invert prose-p:leading-relaxed prose-pre:p-0">
                    <ReactMarkdown>{content}</ReactMarkdown>
                </div>

                {sources && sources.length > 0 && (
                    <div className="mt-4 rounded-md bg-blue-50/50 p-3 text-sm dark:bg-blue-900/20">
                        <p className="mb-2 font-medium text-blue-700 dark:text-blue-300">📚 参考资料 Sources:</p>
                        <ul className="list-inside list-disc space-y-1 text-blue-600 dark:text-blue-400">
                            {sources.map((source, i) => (
                                <li key={i} className="truncate">{source}</li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>
        </div>
    );
}
