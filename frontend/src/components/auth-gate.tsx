"use client";

import React, { useState, useEffect } from "react";
import { Lock, Loader2, AlertCircle } from "lucide-react";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(false);

  // Helper to verify password with Backend
  const verifyPassword = async (pwd: string) => {
    try {
      const res = await fetch(
        `${
          process.env.NEXT_PUBLIC_API_URL || "http://localhost:5001"
        }/api/verify`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Access-Token": pwd,
          },
        }
      );
      return res.ok; // Returns true if 200 OK, false if 401 Unauthorized
    } catch (e) {
      console.error("Verification failed:", e);
      return false;
    }
  };

  useEffect(() => {
    // Check local storage on load
    const saved = localStorage.getItem("app_password");
    if (saved) {
      // Optional: Verify the saved password silently
      verifyPassword(saved).then((isValid) => {
        if (isValid) setIsAuthenticated(true);
        else localStorage.removeItem("app_password");
      });
    }
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(false);
    setIsLoading(true);

    // 1. VERIFY WITH SERVER
    const isValid = await verifyPassword(password);

    if (isValid) {
      // 2. SUCCESS: Save and Unlock
      localStorage.setItem("app_password", password);
      setIsAuthenticated(true);
    } else {
      // 3. FAIL: Show Error
      setError(true);
    }
    setIsLoading(false);
  };

  if (isAuthenticated) {
    return <>{children}</>;
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-zinc-50 dark:bg-black p-4">
      <div className="w-full max-w-md bg-white dark:bg-zinc-900 rounded-xl shadow-xl border border-zinc-200 dark:border-zinc-800 p-8 text-center">
        <div
          className={`mx-auto w-12 h-12 rounded-full flex items-center justify-center mb-6 transition-colors ${
            error
              ? "bg-red-100 text-red-600"
              : "bg-black text-white dark:bg-white dark:text-black"
          }`}
        >
          {error ? (
            <AlertCircle className="w-6 h-6" />
          ) : (
            <Lock className="w-6 h-6" />
          )}
        </div>

        <h1 className="text-2xl font-bold mb-2">内部访问限制</h1>
        <p className="text-zinc-500 mb-8">
          {error ? (
            <span className="text-red-500 font-medium">密码错误，请重试</span>
          ) : (
            "请输入访问密码以继续"
          )}
        </p>

        <form onSubmit={handleLogin} className="space-y-4">
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="访问密码..."
            className={`w-full px-4 py-3 rounded-lg border bg-zinc-50 focus:outline-none focus:ring-2 transition-all text-center
                ${
                  error
                    ? "border-red-300 focus:ring-red-200 bg-red-50"
                    : "border-zinc-200 focus:ring-black dark:bg-zinc-800 dark:border-zinc-700 dark:focus:ring-white"
                }`}
            autoFocus
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={!password || isLoading}
            className="w-full py-3 bg-black text-white rounded-lg font-medium hover:bg-zinc-800 dark:bg-white dark:text-black dark:hover:bg-zinc-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              "进入系统"
            )}
          </button>
        </form>
      </div>
      <p className="mt-8 text-xs text-zinc-400">SiZheng Chatbox • Protected</p>
    </div>
  );
}
