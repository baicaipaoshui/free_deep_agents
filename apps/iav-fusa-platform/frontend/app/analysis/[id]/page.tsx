"use client";

import { useState, useRef, useEffect } from "react";
import { useParams } from "next/navigation";
import useSWR from "swr";
import { api, AnalysisType, AnalysisSession, PendingApproval } from "@/lib/api";
import { AgentPanel } from "@/components/AgentPanel";
import { PipelineProgress } from "@/components/PipelineProgress";
import { ApprovalDialog } from "@/components/ApprovalDialog";

const ANALYSIS_TYPES: { value: AnalysisType; label: string; desc: string }[] = [
  { value: "hara", label: "HARA", desc: "危害分析与风险评估" },
  { value: "fmea", label: "FMEA", desc: "失效模式与影响分析" },
  { value: "fta",  label: "FTA",  desc: "故障树分析" },
  { value: "full", label: "全流程", desc: "HARA → FMEA → FTA" },
];

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
}

export default function AnalysisPage() {
  const { id: projectId } = useParams<{ id: string }>();
  const [analysisType, setAnalysisType] = useState<AnalysisType>("hara");
  const [inputText, setInputText] = useState("");
  const [activeSession, setActiveSession] = useState<AnalysisSession | null>(null);
  const [pendingApproval, setPendingApproval] = useState<PendingApproval | null>(null);
  const [approvalOpen, setApprovalOpen] = useState(false);

  const [currentStage, setCurrentStage] = useState<string | undefined>();
  const [awaitingApproval, setAwaitingApproval] = useState(false);
  const [isRunning, setIsRunning] = useState(false);

  // Conversation history — append-only
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [replyText, setReplyText] = useState("");
  const [replying, setReplying] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { data: project } = useSWR(`/api/projects/${projectId}`, () =>
    api.projects.get(projectId),
  );

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const addMessage = (role: "user" | "assistant", content: string) => {
    setMessages((prev) => [
      ...prev,
      { id: `${Date.now()}-${Math.random()}`, role, content },
    ]);
  };

  const handleStart = async () => {
    if (!inputText.trim()) return;
    setCurrentStage(undefined);
    setAwaitingApproval(false);
    setIsRunning(true);
    addMessage("user", inputText);
    const session = await api.analysis.start({
      project_id: projectId,
      analysis_type: analysisType,
      input_text: inputText,
    });
    setActiveSession(session);
  };

  const handleApprovalRequired = (gateType: string, data: unknown) => {
    if (!activeSession) return;
    setAwaitingApproval(true);
    setPendingApproval({
      session_id: activeSession.session_id,
      project_id: projectId,
      analysis_type: analysisType,
      gate_type: gateType,
      gate_data: data as Record<string, unknown>,
      created_at: new Date().toISOString(),
    });
    setApprovalOpen(true);
  };

  const handleProgress = (stage: string) => {
    setCurrentStage(stage);
    setAwaitingApproval(false);
  };

  const handleComplete = (result: Record<string, unknown>) => {
    setAwaitingApproval(false);
    setIsRunning(false);
    setReplying(false);
    const summary = (result?.summary as string) ?? "";
    if (summary) {
      addMessage("assistant", summary);
    }
  };

  const handleReply = async () => {
    if (!replyText.trim() || !activeSession) return;
    const text = replyText;
    setReplyText("");
    setReplying(true);
    setIsRunning(true);
    setCurrentStage(undefined);
    addMessage("user", text);
    await api.analysis.reply(activeSession.session_id, text);
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col">
      {/* Header */}
      <header className="border-b border-gray-800 px-8 py-4 flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-xl font-bold">{project?.name ?? "分析工作台"}</h1>
          <p className="text-gray-500 text-sm">{project?.vehicle_system}</p>
        </div>
        <a href="/approval" className="text-sm text-yellow-400 hover:text-yellow-300 transition-colors">
          审批队列 →
        </a>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* ── Left: Input & Config ── */}
        <div className="w-80 shrink-0 border-r border-gray-800 p-5 flex flex-col gap-4 overflow-y-auto">
          <div>
            <label className="block text-xs text-gray-400 mb-2">分析类型</label>
            <div className="grid grid-cols-2 gap-2">
              {ANALYSIS_TYPES.map((t) => (
                <button
                  key={t.value}
                  onClick={() => setAnalysisType(t.value)}
                  disabled={!!activeSession}
                  className={`p-2.5 rounded-lg border text-left transition-colors disabled:opacity-50 ${
                    analysisType === t.value
                      ? "border-blue-500 bg-blue-900/30 text-blue-200"
                      : "border-gray-700 hover:border-gray-600 text-gray-400"
                  }`}
                >
                  <div className="text-sm font-semibold">{t.label}</div>
                  <div className="text-xs opacity-70">{t.desc}</div>
                </button>
              ))}
            </div>
          </div>

          <div className="flex-1">
            <label className="block text-xs text-gray-400 mb-2">系统 / Item 描述</label>
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              disabled={!!activeSession}
              rows={10}
              placeholder={"描述待分析的系统，包括：\n- 系统名称和功能\n- 工作范围和边界\n- 已知约束条件"}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none disabled:opacity-50"
            />
          </div>

          <button
            onClick={handleStart}
            disabled={!inputText.trim() || !!activeSession}
            className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed py-2.5 rounded-lg text-sm font-medium transition-colors"
          >
            {activeSession ? "分析进行中…" : "启动分析"}
          </button>

          {/* New analysis button after session exists */}
          {activeSession && !isRunning && (
            <button
              onClick={() => {
                setActiveSession(null);
                setMessages([]);
                setInputText("");
                setCurrentStage(undefined);
                setAwaitingApproval(false);
                setIsRunning(false);
              }}
              className="w-full border border-gray-600 hover:border-gray-500 text-gray-400 hover:text-gray-200 py-2 rounded-lg text-sm transition-colors"
            >
              新建分析
            </button>
          )}
        </div>

        {/* ── Center: Chat history + Agent streaming ── */}
        <div className="flex-1 flex flex-col min-h-0">

          {/* Agent real-time panel — shown while running */}
          {activeSession && isRunning && (
            <div className="shrink-0 border-b border-gray-800">
              <AgentPanel
                sessionId={activeSession.session_id}
                onApprovalRequired={handleApprovalRequired}
                onComplete={handleComplete}
                onProgress={handleProgress}
              />
            </div>
          )}

          {/* Conversation messages */}
          <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
            {messages.length === 0 && !isRunning && (
              <div className="h-full flex items-center justify-center text-gray-600">
                <p>填写系统描述后点击「启动分析」</p>
              </div>
            )}

            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {msg.role === "assistant" && (
                  <div className="w-7 h-7 rounded-full bg-blue-700 flex items-center justify-center text-xs shrink-0 mr-2 mt-1">
                    AI
                  </div>
                )}
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
                    msg.role === "user"
                      ? "bg-blue-600 text-white rounded-tr-sm"
                      : "bg-gray-800 text-gray-200 border border-gray-700 rounded-tl-sm font-mono"
                  }`}
                >
                  {msg.content}
                  {msg.role === "assistant" && (
                    <div className="mt-2 flex gap-2">
                      <button
                        onClick={() => navigator.clipboard.writeText(msg.content)}
                        className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
                      >
                        复制
                      </button>
                    </div>
                  )}
                </div>
                {msg.role === "user" && (
                  <div className="w-7 h-7 rounded-full bg-gray-600 flex items-center justify-center text-xs shrink-0 ml-2 mt-1">
                    我
                  </div>
                )}
              </div>
            ))}

            {/* Thinking indicator */}
            {isRunning && messages.length > 0 && (
              <div className="flex justify-start">
                <div className="w-7 h-7 rounded-full bg-blue-700 flex items-center justify-center text-xs shrink-0 mr-2 mt-1">
                  AI
                </div>
                <div className="bg-gray-800 border border-gray-700 rounded-2xl rounded-tl-sm px-4 py-3">
                  <span className="inline-flex gap-1">
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
                  </span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Reply input — shown after session starts */}
          {activeSession && (
            <div className="shrink-0 border-t border-gray-800 p-4 flex gap-3">
              <textarea
                value={replyText}
                onChange={(e) => setReplyText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleReply();
                  }
                }}
                placeholder="追问或补充信息… (Enter 发送，Shift+Enter 换行)"
                disabled={isRunning || replying}
                rows={2}
                className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-sm text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50 resize-none"
              />
              <button
                onClick={handleReply}
                disabled={!replyText.trim() || isRunning || replying}
                className="bg-blue-600 hover:bg-blue-500 disabled:opacity-40 px-4 rounded-xl text-sm font-medium transition-colors self-end pb-2.5 pt-2.5"
              >
                {replying ? "发送中…" : "发送"}
              </button>
            </div>
          )}
        </div>

        {/* ── Right: Pipeline stage tracker ── */}
        <div className="w-64 shrink-0 border-l border-gray-800 p-5 overflow-y-auto">
          {analysisType !== "full" && (
            <PipelineProgress
              analysisType={analysisType}
              currentStage={currentStage}
              awaitingApproval={awaitingApproval}
            />
          )}
        </div>
      </div>

      {/* Approval dialog */}
      {pendingApproval && (
        <ApprovalDialog
          approval={pendingApproval}
          open={approvalOpen}
          onOpenChange={setApprovalOpen}
          onDecision={() => {
            setPendingApproval(null);
            setAwaitingApproval(false);
          }}
        />
      )}
    </div>
  );
}
