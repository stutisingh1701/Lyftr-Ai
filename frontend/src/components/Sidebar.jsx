import React from 'react';
import { 
  PlusCircle, 
  Settings2, 
  Activity, 
  ShieldAlert, 
  Database, 
  Cpu, 
  ExternalLink,
  MessageSquare
} from 'lucide-react';

export default function Sidebar({
  sessionId,
  onNewChat,
  health,
  systemPrompt,
  setSystemPrompt,
  simulateHeader,
  setSimulateHeader
}) {
  return (
    <aside className="w-80 bg-slate-950 border-r border-slate-800/80 flex flex-col h-full select-none">
      {/* Brand Header */}
      <div className="p-5 border-b border-slate-800/80 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-600/30">
            <Cpu className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-slate-100 tracking-tight text-lg leading-tight">Lyftr AI</h1>
            <span className="text-[11px] text-slate-400 font-medium tracking-wide uppercase">Resilient LLM Chat</span>
          </div>
        </div>
      </div>

      {/* New Chat Button */}
      <div className="p-4 border-b border-slate-800/60">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-all duration-200 shadow-md shadow-indigo-600/20 active:scale-98"
        >
          <PlusCircle className="w-4 h-4" />
          <span>New Chat</span>
        </button>
      </div>

      {/* Controls & Configuration */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* Active Session Info */}
        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-3 text-xs">
          <div className="flex items-center justify-between mb-1 text-slate-400">
            <span className="font-medium flex items-center gap-1.5">
              <MessageSquare className="w-3.5 h-3.5 text-indigo-400" />
              Active Session
            </span>
          </div>
          <p className="font-mono text-slate-200 break-all bg-slate-950/60 p-2 rounded-lg border border-slate-800 text-[11px]">
            {sessionId}
          </p>
        </div>

        {/* System Prompt (Optional Requirement) */}
        <div className="space-y-2">
          <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
            <Settings2 className="w-3.5 h-3.5 text-indigo-400" />
            System Prompt
          </label>
          <textarea
            data-testid="system-prompt-input"
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            placeholder="e.g. You are a senior AI research scientist..."
            rows={3}
            className="w-full bg-slate-900/80 border border-slate-800 rounded-xl p-2.5 text-xs text-slate-200 placeholder-slate-500 outline-none focus:border-indigo-500 transition-colors resize-none"
          />
          <p className="text-[11px] text-slate-500 leading-tight">Overrides the default system prompt for this session.</p>
        </div>

        {/* Failure Simulation Test Hook (Evaluator Feature) */}
        <div className="space-y-2">
          <label className="text-xs font-semibold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
            <ShieldAlert className="w-3.5 h-3.5" />
            X-Simulate-Failure Hook
          </label>
          <select
            value={simulateHeader}
            onChange={(e) => setSimulateHeader(e.target.value)}
            className="w-full bg-slate-900/90 border border-amber-500/30 text-amber-200 text-xs rounded-xl p-2.5 outline-none focus:border-amber-400 transition-colors cursor-pointer"
          >
            <option value="none">Normal (No simulation)</option>
            <option value="key_1=429">key_1=429 (Failover to key_2)</option>
            <option value="key_1=500">key_1=500 (Failover to key_2)</option>
            <option value="key_1=429,key_2=500">key_1=429, key_2=500 (Failover chain)</option>
            <option value="*=429">*=429 (All keys fail -&gt; 503)</option>
          </select>
          <p className="text-[11px] text-slate-400 leading-tight">
            Demonstrates on-demand failover without burning real API provider quotas.
          </p>
        </div>

        {/* Backend & Cluster Status */}
        <div className="bg-slate-900/40 border border-slate-800/80 rounded-xl p-3 space-y-2.5 text-xs">
          <div className="font-semibold text-slate-300 flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-emerald-400" />
            System Health
          </div>
          <div className="space-y-1.5 text-slate-400 text-[11px]">
            <div className="flex justify-between items-center">
              <span>Status:</span>
              <span className={`font-semibold ${health?.status === 'ok' ? 'text-emerald-400' : 'text-amber-400'}`}>
                {health?.status || 'Connecting...'}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span>Keys Configured:</span>
              <span className="font-mono text-slate-200">{health?.keys_configured ?? '-'}</span>
            </div>
            <div className="flex justify-between items-center">
              <span>Response Caching:</span>
              <span className={`font-semibold ${health?.cache_enabled ? 'text-emerald-400' : 'text-slate-500'}`}>
                {health?.cache_enabled ? 'Active (LiteLLM)' : 'Disabled'}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span>Storage:</span>
              <span className="text-slate-200">SQLite (/data/app.db)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Footer Info */}
      <div className="p-4 border-t border-slate-800/80 text-[11px] text-slate-500 flex justify-between items-center">
        <span>Lyftr AI v1.0.0</span>
        <span className="text-slate-400">Zero-Cost Stack</span>
      </div>
    </aside>
  );
}
