import React, { useState, useEffect, useRef } from 'react';
import { fetchHealth, sendChatMessage, fetchSessionMessages } from './services/api';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import Sidebar from './components/Sidebar';
import { Sparkles, Bot, ShieldCheck, Zap, AlertTriangle, Menu, X } from 'lucide-react';

function generateSessionId() {
  return `s-${Math.random().toString(36).substring(2, 10)}`;
}

export default function App() {
  const [sessionId, setSessionId] = useState(() => generateSessionId());
  const [messages, setMessages] = useState([]);
  const [systemPrompt, setSystemPrompt] = useState('');
  const [simulateHeader, setSimulateHeader] = useState('none');
  const [loading, setLoading] = useState(false);
  const [health, setHealth] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const messagesEndRef = useRef(null);

  // Poll health on mount
  useEffect(() => {
    async function checkHealth() {
      try {
        const data = await fetchHealth();
        setHealth(data);
      } catch (err) {
        console.error('Health check error:', err);
      }
    }
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleNewChat = () => {
    const newId = generateSessionId();
    setSessionId(newId);
    setMessages([]);
    setSidebarOpen(false);
  };

  const handleSendMessage = async (text) => {
    if (!text.trim() || loading) return;

    // Append user message immediately
    const userMsg = {
      role: 'user',
      content: text,
      created_at: new Date().toISOString()
    };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const data = await sendChatMessage({
        sessionId,
        message: text,
        systemPrompt,
        simulateHeader
      });

      const assistantMsg = {
        role: 'assistant',
        content: data.reply,
        metadata: data.metadata,
        created_at: new Date().toISOString()
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      console.error('Chat error:', err);
      const errorMsg = {
        role: 'assistant',
        content: err.detail || err.message || 'An unexpected error occurred.',
        isError: true,
        status: err.status || 503,
        created_at: new Date().toISOString()
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden">
      {/* Mobile Sidebar Backdrop */}
      {sidebarOpen && (
        <div 
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 bg-black/60 z-30 lg:hidden backdrop-blur-sm"
        />
      )}

      {/* Sidebar (Desktop + Mobile Drawer) */}
      <div className={`fixed inset-y-0 left-0 z-40 transform lg:static lg:transform-none transition-transform duration-200 ease-in-out ${
        sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
      }`}>
        <Sidebar
          sessionId={sessionId}
          onNewChat={handleNewChat}
          health={health}
          systemPrompt={systemPrompt}
          setSystemPrompt={setSystemPrompt}
          simulateHeader={simulateHeader}
          setSimulateHeader={setSimulateHeader}
        />
      </div>

      {/* Main Chat Viewport */}
      <main className="flex-1 flex flex-col h-full overflow-hidden bg-gradient-to-b from-slate-950 via-slate-900/60 to-slate-950">
        {/* Top Navigation Bar */}
        <header className="h-14 border-b border-slate-800/80 px-4 flex items-center justify-between shrink-0 bg-slate-950/40 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="lg:hidden p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-white"
            >
              {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-200 text-sm hidden sm:inline">Session:</span>
              <span className="font-mono text-xs bg-slate-900 px-2.5 py-1 rounded-md border border-slate-800 text-indigo-300">
                {sessionId}
              </span>
            </div>
          </div>

          {/* Quick Simulation Indicator Pill */}
          <div className="flex items-center gap-2">
            {simulateHeader !== 'none' && (
              <div className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs">
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>Simulating: {simulateHeader}</span>
              </div>
            )}
            <button
              onClick={handleNewChat}
              className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-xs font-medium text-slate-200 transition-colors"
            >
              Reset Session
            </button>
          </div>
        </header>

        {/* Message Feed */}
        <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8">
          <div className="max-w-4xl mx-auto">
            {messages.length === 0 ? (
              /* Empty State Hero */
              <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
                <div className="w-16 h-16 rounded-3xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-violet-500 flex items-center justify-center shadow-xl shadow-indigo-600/30 mb-6">
                  <Bot className="w-8 h-8 text-white" />
                </div>
                <h2 className="text-2xl md:text-3xl font-bold tracking-tight text-white mb-3">
                  Welcome to Lyftr AI
                </h2>
                <p className="max-w-md text-sm md:text-base text-slate-400 mb-8 leading-relaxed">
                  Enterprise-grade conversational AI platform featuring zero-downtime key failover, LiteLLM semantic caching, and persistent session memory.
                </p>

                {/* Feature Cards */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full max-w-2xl text-left">
                  <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm">
                    <div className="w-8 h-8 rounded-lg bg-emerald-950/60 border border-emerald-500/40 text-emerald-400 flex items-center justify-center mb-2.5">
                      <Zap className="w-4 h-4" />
                    </div>
                    <div className="font-semibold text-sm text-slate-200 mb-1">LiteLLM Caching</div>
                    <div className="text-xs text-slate-400 leading-relaxed">Deterministic response cache reduces latency and API costs.</div>
                  </div>

                  <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm">
                    <div className="w-8 h-8 rounded-lg bg-indigo-950/60 border border-indigo-500/40 text-indigo-400 flex items-center justify-center mb-2.5">
                      <ShieldCheck className="w-4 h-4" />
                    </div>
                    <div className="font-semibold text-sm text-slate-200 mb-1">Key Failover</div>
                    <div className="text-xs text-slate-400 leading-relaxed">Automatic failover across multiple keys on 429, quota, or 5xx.</div>
                  </div>

                  <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm">
                    <div className="w-8 h-8 rounded-lg bg-violet-950/60 border border-violet-500/40 text-violet-400 flex items-center justify-center mb-2.5">
                      <Sparkles className="w-4 h-4" />
                    </div>
                    <div className="font-semibold text-sm text-slate-200 mb-1">Per-Request Usage</div>
                    <div className="text-xs text-slate-400 leading-relaxed">Precise input and output token counts with every reply.</div>
                  </div>
                </div>
              </div>
            ) : (
              /* Message List */
              messages.map((msg, index) => (
                <ChatMessage key={index} message={msg} />
              ))
            )}

            {/* In-Flight Thinking / Loading Indicator */}
            {loading && (
              <div className="flex justify-start mb-6">
                <div className="rounded-2xl rounded-tl-sm bg-slate-900/80 border border-slate-800 px-5 py-4 text-slate-300 shadow-lg flex items-center gap-3">
                  <div className="flex gap-1.5">
                    <div className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce [animation-delay:-0.3s]"></div>
                    <div className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce [animation-delay:-0.15s]"></div>
                    <div className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce"></div>
                  </div>
                  <span className="text-xs font-medium text-slate-400">Processing completion...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Message Input Bar */}
        <div className="p-4 md:px-8 border-t border-slate-800/80 bg-slate-950/60 backdrop-blur-md">
          <div className="max-w-4xl mx-auto">
            <ChatInput onSendMessage={handleSendMessage} disabled={loading} />
            <div className="flex justify-between items-center mt-2 px-1 text-[11px] text-slate-500">
              <span>Shift + Enter for new line</span>
              <span>All requests stored securely in SQLite</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
