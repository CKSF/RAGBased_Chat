import { ChatInterface } from "@/components/chat-interface";

export default function Home() {
  return (
    <main className="flex h-screen flex-col items-center bg-zinc-50 dark:bg-black font-sans overflow-hidden">
      <div className="z-10 w-full max-w-5xl items-center justify-between font-mono text-sm flex p-2 md:p-4 shrink-0">
        <p className="fixed left-0 top-0 flex w-full justify-center border-b border-gray-300 bg-gradient-to-b from-zinc-200 backdrop-blur-2xl dark:border-neutral-800 dark:bg-zinc-800/30 dark:from-inherit lg:static lg:w-auto  lg:rounded-xl lg:border lg:bg-gray-200 lg:p-4 lg:dark:bg-zinc-800/30">
          思政领域 RAG 大模型应用&nbsp;
          <code className="font-mono font-bold">SiZheng Chatbox</code>
        </p>
        <div className="fixed bottom-0 left-0 flex h-48 w-full items-end justify-center bg-gradient-to-t from-white via-white dark:from-black dark:via-black lg:static lg:size-auto lg:bg-none">
          <a
            className="pointer-events-none flex place-items-center gap-2 p-8 lg:pointer-events-auto lg:p-0"
            href="#"
            target="_blank"
            rel="noopener noreferrer"
          >
            By SiZheng Team
          </a>
        </div>
      </div>
      <div className="w-full max-w-4xl flex-1 flex flex-col min-h-[600px]">
        <ChatInterface />
      </div>
    </main>
  );
}
