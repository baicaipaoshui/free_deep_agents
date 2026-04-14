"use client";

import { useState } from "react";
import useSWR, { mutate } from "swr";
import { api, PendingApproval } from "@/lib/api";
import { ApprovalDialog } from "@/components/ApprovalDialog";
import { Clock, CheckCircle } from "lucide-react";

const fetcher = () => api.approval.list();

const GATE_LABELS: Record<string, string> = {
  asil_confirmation: "ASIL 定级确认",
  rpn_review: "高 RPN 失效模式审核",
  fta_logic_check: "FTA 逻辑校验",
};

export default function ApprovalPage() {
  const { data: approvals, isLoading } = useSWR<PendingApproval[]>("/api/approval", fetcher, {
    refreshInterval: 5000,
  });
  const [selected, setSelected] = useState<PendingApproval | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  const handleSelect = (a: PendingApproval) => {
    setSelected(a);
    setDialogOpen(true);
  };

  const handleDecision = async () => {
    await mutate("/api/approval");
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-8">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold">人工审批队列</h1>
            <p className="text-gray-400 text-sm mt-1">
              ASIL 确认 · RPN 审核 · FTA 逻辑校验
            </p>
          </div>
          <span className="bg-yellow-900/40 border border-yellow-700 text-yellow-400 text-sm px-3 py-1 rounded-full">
            {approvals?.length ?? 0} 待处理
          </span>
        </div>

        {isLoading ? (
          <p className="text-gray-500">加载中…</p>
        ) : approvals?.length === 0 ? (
          <div className="text-center py-20">
            <CheckCircle className="w-12 h-12 text-green-600 mx-auto mb-3" />
            <p className="text-gray-500">暂无待审批项目</p>
          </div>
        ) : (
          <div className="space-y-3">
            {approvals?.map((a) => (
              <button
                key={a.session_id}
                onClick={() => handleSelect(a)}
                className="w-full bg-gray-800 rounded-xl border border-yellow-800/50 hover:border-yellow-600 p-5 text-left transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-yellow-400 text-xs font-mono bg-yellow-900/30 px-2 py-0.5 rounded">
                        {GATE_LABELS[a.gate_type] ?? a.gate_type}
                      </span>
                      <span className="text-xs text-gray-500 uppercase">{a.analysis_type}</span>
                    </div>
                    <p className="text-sm text-gray-300 font-mono">
                      {a.session_id.slice(0, 12)}…
                    </p>
                    <p className="text-xs text-gray-600 mt-1">
                      创建于 {new Date(a.created_at).toLocaleString("zh-CN")}
                    </p>
                  </div>
                  <Clock className="w-5 h-5 text-yellow-500 shrink-0" />
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {selected && (
        <ApprovalDialog
          approval={selected}
          open={dialogOpen}
          onOpenChange={setDialogOpen}
          onDecision={handleDecision}
        />
      )}
    </div>
  );
}
