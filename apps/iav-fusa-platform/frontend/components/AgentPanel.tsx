"use client";

import { useEffect, useRef, useState } from "react";
import { connectAnalysisWS, api } from "@/lib/api";

interface AgentEvent {
  type: string;
  status?: string;
  stage?: string;
  message?: string;
  agent?: string;
  tool?: string;
  input?: Record<string, unknown>;
  result?: Record<string, unknown> | string;
  gate_type?: string;
  data?: unknown;
  error?: string;
}

interface AgentPanelProps {
  sessionId: string;
  onApprovalRequired?: (gateType: string, data: unknown) => void;
  onComplete?: (result: Record<string, unknown>) => void;
  onProgress?: (stage: string) => void;
}

const EVENT_STYLE: Record<string, string> = {
  status:            "text-blue-400",
  progress:          "text-green-400",
  subagent:          "text-purple-400 font-semibold",
  tool_start:        "text-cyan-400",
  tool_end:          "text-cyan-600",
  approval_required: "text-yellow-400 font-semibold",
  complete:          "text-emerald-400 font-semibold",
  error:             "text-red-400 font-semibold",
};

const EVENT_ICON: Record<string, string> = {
  status:            "●",
  progress:          "▶",
  subagent:          "◈",
  tool_start:        "⚙",
  tool_end:          "✓",
  approval_required: "⚠",
  complete:          "✔",
  error:             "✗",
};

function renderEvent(e: AgentEvent): string {
  switch (e.type) {
    case "status":   return `状态: ${e.status}`;
    case "progress": return e.message ?? `[${e.stage}]`;
    case "subagent": return e.message ?? e.agent ?? "";
    case "tool_start": return e.message ?? `调用工具: ${e.tool}`;
    case "tool_end": return `${e.tool} 完成`;
    case "approval_required": return `人工审批门: ${e.gate_type} — 请在审批队列处理`;
    case "complete": return "分析完成";
    case "error":    return `错误: ${e.error}`;
    default:         return e.message ?? e.type;
  }
}

export function AgentPanel({
  sessionId,
  onApprovalRequired,
  onComplete,
  onProgress,
}: AgentPanelProps) {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [thinking, setThinking] = useState(false); // 模型推理中 indicator
  const bottomRef = useRef<HTMLDivElement>(null);

  // Use refs for callbacks so the WebSocket effect only runs once per sessionId.
  // Without this, inline function props recreate on every render → WS reconnects.
  const onApprovalRequiredRef = useRef(onApprovalRequired);
  const onCompleteRef = useRef(onComplete);
  const onProgressRef = useRef(onProgress);
  useEffect(() => {
    onApprovalRequiredRef.current = onApprovalRequired;
    onCompleteRef.current = onComplete;
    onProgressRef.current = onProgress;
  });

  useEffect(() => {
    setEvents([]);
    setThinking(true);
    let done = false;

    // HTTP polling fallback: if WS misses the complete event, poll until done
    const poll = setInterval(async () => {
      if (done) { clearInterval(poll); return; }
      try {
        const s = await api.analysis.get(sessionId);
        if (s.status === "completed") {
          done = true;
          clearInterval(poll);
          setThinking(false);
          if (s.result) onCompleteRef.current?.(s.result as Record<string, unknown>);
          setEvents((prev) => {
            const alreadyComplete = prev.some((e) => e.type === "complete");
            return alreadyComplete ? prev : [...prev, { type: "complete" }];
          });
        } else if (s.status === "failed") {
          done = true;
          clearInterval(poll);
          setThinking(false);
          setEvents((prev) => [...prev, { type: "error", error: s.error ?? "分析失败" }]);
        }
      } catch { /* ignore */ }
    }, 5000);

    const ws = connectAnalysisWS(
      sessionId,
      (event) => {
        const e = event as unknown as AgentEvent;
        if (e.type === "token" || e.type === "ping") return;

        // Any meaningful event → hide the "thinking" spinner
        if (e.type !== "status") setThinking(false);

        setEvents((prev) => [...prev, e]);

        if (e.type === "progress" && e.stage) {
          onProgressRef.current?.(e.stage);
        }
        if (e.type === "approval_required") {
          onApprovalRequiredRef.current?.(e.gate_type ?? "unknown", e.data);
        }
        if (e.type === "complete" && e.result) {
          done = true;
          clearInterval(poll);
          setThinking(false);
          onCompleteRef.current?.(e.result as Record<string, unknown>);
        }
        if (e.type === "error") {
          done = true;
          clearInterval(poll);
          setThinking(false);
        }
      },
      () => {
        setConnected(false);
        setThinking(false);
      },
    );

    ws.onopen = () => setConnected(true);

    return () => { ws.close(); clearInterval(poll); };
  }, [sessionId]); // ← 只依赖 sessionId，不依赖回调函数，避免重连

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events, thinking]);

  const visible = events.filter((e) => e.type !== "ping");

  return (
    <div className="flex flex-col h-full bg-gray-900 rounded-lg border border-gray-700">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
        <h3 className="text-sm font-medium text-gray-200">Agent 实时输出</h3>
        <span className={`flex items-center gap-1.5 text-xs ${connected ? "text-green-400" : "text-gray-500"}`}>
          <span className={`w-2 h-2 rounded-full ${connected ? "bg-green-400 animate-pulse" : "bg-gray-500"}`} />
          {connected ? "已连接" : "未连接"}
        </span>
      </div>

      {/* Legend */}
      <div className="flex gap-3 px-4 py-2 border-b border-gray-800 text-xs text-gray-600 flex-wrap">
        <span className="text-green-500">▶ 阶段</span>
        <span className="text-purple-400">◈ 子代理</span>
        <span className="text-cyan-400">⚙ 工具调用</span>
        <span className="text-yellow-400">⚠ 审批门</span>
      </div>

      {/* Event stream */}
      <div className="flex-1 overflow-y-auto p-4 font-mono text-xs space-y-1">
        {visible.length === 0 && !thinking && (
          <p className="text-gray-600 italic">等待 Agent 输出…</p>
        )}

        {visible.map((e, idx) => (
          <div key={idx} className={`flex gap-2 ${EVENT_STYLE[e.type] ?? "text-gray-300"}`}>
            <span className="shrink-0 w-4 mt-px">{EVENT_ICON[e.type] ?? "○"}</span>
            <span className="break-all">{renderEvent(e)}</span>
          </div>
        ))}

        {/* 模型推理中 indicator */}
        {thinking && (
          <div className="flex gap-2 text-gray-500 items-center mt-1">
            <span className="shrink-0 w-4">
              <span className="inline-block w-3 h-3 border-2 border-gray-500 border-t-blue-400 rounded-full animate-spin" />
            </span>
            <span>模型推理中，请稍候…</span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
