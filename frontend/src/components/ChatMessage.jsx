import React from 'react';
import { Zap, Sparkles, Clock, Database, KeyRound, AlertCircle, Cpu } from 'lucide-react';

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user';
  const isError = message.isError;
  const metadata = message.metadata;

  if (isUser) {
    return (
      <div className="flex justify-end mb-4 animate-fade-in">
        <div className="max-w-[80%] md:max-w-[70%] rounded-2xl rounded-tr-sm bg-gradient-to-r from-indigo-600 to-indigo-700 text-white px-4 py-3 shadow-md shadow-indigo-950/20">
          <p className="whitespace-pre-wrap break-words text-sm md:text-base leading-relaxed">{message.content}</p>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex justify-start mb-4">
        <div className="max-w-[85%] md:max-w-[75%] rounded-2xl rounded-tl-sm bg-red-950/40 border border-red-500/30 text-red-200 px-4 py-3 shadow-sm flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 mt-0.5 shrink-0" />
          <div>
            <div className="font-semibold text-red-300 text-sm">Provider Error ({message.status || 503})</div>
            <p className="text-sm text-red-200/90 whitespace-pre-wrap break-words mt-1">{message.content}</p>
          </div>
        </div>
      </div>
    );
  }

  const isCache = metadata?.resolution_source === 'LLM_CACHE';

  return (
    <div className="flex justify-start mb-6" data-testid="assistant-message">
      <div className="max-w-[90%] md:max-w-[80%] rounded-2xl rounded-tl-sm bg-slate-900/90 border border-slate-800 text-slate-100 shadow-xl overflow-hidden backdrop-blur-sm">
        {/* Message Content */}
        <div className="px-5 py-4">
          <p className="whitespace-pre-wrap break-words text-sm md:text-base leading-relaxed text-slate-200">{message.content}</p>
        </div>

        {/* Metadata Footer */}
        {metadata && (
          <div className="bg-slate-950/80 border-t border-slate-800/80 px-4 py-2.5 flex flex-wrap items-center gap-2 text-xs">
            {/* Resolution Source Badge */}
            <div 
              data-testid="meta-source"
              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md font-semibold tracking-wide border shadow-sm ${
                isCache 
                  ? 'bg-emerald-950/60 border-emerald-500/40 text-emerald-400' 
                  : 'bg-indigo-950/60 border-indigo-500/40 text-indigo-400'
              }`}
            >
              {isCache ? <Zap className="w-3.5 h-3.5" /> : <Sparkles className="w-3.5 h-3.5" />}
              <span>{metadata.resolution_source}</span>
            </div>

            {/* Model Badge */}
            <div 
              data-testid="meta-model"
              className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-slate-800/80 text-slate-300 border border-slate-700/50"
              title="LiteLLM Model"
            >
              <Cpu className="w-3.5 h-3.5 text-slate-400" />
              <span>{metadata.model}</span>
            </div>

            {/* Latency Badge */}
            <div 
              data-testid="meta-latency"
              className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-slate-800/80 text-slate-300 border border-slate-700/50 font-mono"
              title="Server-measured Latency"
            >
              <Clock className="w-3.5 h-3.5 text-amber-400" />
              <span>{metadata.latency_ms} ms</span>
            </div>

            {/* Token Usage Badges */}
            <div className="inline-flex items-center gap-2 px-2 py-1 rounded-md bg-slate-800/80 border border-slate-700/50 text-slate-300">
              <span className="text-slate-400">Tokens:</span>
              <span title="Input Tokens" className="flex items-center gap-0.5">
                <span className="text-slate-400">in:</span>
                <span data-testid="meta-input-tokens" className="font-semibold text-slate-200">{metadata.input_tokens}</span>
              </span>
              <span className="text-slate-600">|</span>
              <span title="Output Tokens" className="flex items-center gap-0.5">
                <span className="text-slate-400">out:</span>
                <span data-testid="meta-output-tokens" className="font-semibold text-slate-200">{metadata.output_tokens}</span>
              </span>
            </div>

            {/* Key ID & Fallback Info */}
            {metadata.key_id ? (
              <div className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-slate-800/60 text-slate-400 border border-slate-700/40 text-[11px]" title="Key Pool Identifier">
                <KeyRound className="w-3 h-3 text-slate-400" />
                <span>{metadata.key_id}</span>
                {metadata.fallback_attempts > 0 && (
                  <span className="text-amber-400 ml-0.5">({metadata.fallback_attempts} fallback{metadata.fallback_attempts > 1 ? 's' : ''})</span>
                )}
              </div>
            ) : isCache ? (
              <div className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-emerald-950/30 text-emerald-400/80 border border-emerald-500/20 text-[11px]">
                <span>Cache hit (0 API calls)</span>
              </div>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}
