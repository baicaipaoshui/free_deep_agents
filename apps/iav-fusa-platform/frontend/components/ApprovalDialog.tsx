"use client";

import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { api, PendingApproval } from "@/lib/api";

interface ApprovalDialogProps {
  approval: PendingApproval;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDecision: () => void;
}

/**
 * ApprovalDialog presents an analysis gate to a human reviewer.
 * Used for ASIL confirmation gates and high-RPN review gates.
 */
export function ApprovalDialog({
  approval,
  open,
  onOpenChange,
  onDecision,
}: ApprovalDialogProps) {
  const [comment, setComment] = useState("");
  const [reviewerId, setReviewerId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const gateLabels: Record<string, string> = {
    asil_confirmation: "ASIL 定级确认",
    rpn_review: "高 RPN 失效模式审核",
    fta_logic_check: "FTA 逻辑校验",
  };

  const handleDecision = async (approved: boolean) => {
    setLoading(true);
    setError(null);
    try {
      if (approved) {
        await api.approval.approve(approval.session_id, { approved, comment, reviewer_id: reviewerId || "engineer" });
      } else {
        await api.approval.reject(approval.session_id, { approved, comment, reviewer_id: reviewerId || "engineer" });
      }
      onDecision();
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    } finally {
      setLoading(false);
    }
  };

  const renderGateData = () => {
    const data = approval.gate_data;
    if (!data) return null;

    if (approval.gate_type === "asil_confirmation") {
      const ratings = (data.data as Record<string, unknown>[]) ?? [];
      return (
        <div className="mt-3">
          <p className="text-sm font-medium text-gray-300 mb-2">S/E/C/O 评估结果：</p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-gray-300 border-collapse">
              <thead>
                <tr className="border-b border-gray-600">
                  <th className="text-left p-2">场景</th>
                  <th className="p-2">S</th>
                  <th className="p-2">E</th>
                  <th className="p-2">C</th>
                  <th className="p-2 font-semibold">ASIL</th>
                </tr>
              </thead>
              <tbody>
                {ratings.map((r, i) => (
                  <tr key={i} className="border-b border-gray-700">
                    <td className="p-2">{String(r.scenario ?? "—")}</td>
                    <td className="p-2 text-center">{String(r.severity ?? "—")}</td>
                    <td className="p-2 text-center">{String(r.exposure ?? "—")}</td>
                    <td className="p-2 text-center">{String(r.controllability ?? "—")}</td>
                    <td className="p-2 text-center font-bold text-yellow-400">{String(r.asil ?? "—")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      );
    }

    if (approval.gate_type === "rpn_review") {
      const modes = (data.data as Record<string, unknown>[]) ?? [];
      return (
        <div className="mt-3">
          <p className="text-sm font-medium text-gray-300 mb-2">
            高 RPN 失效模式（{modes.length} 项）：
          </p>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {modes.map((m, i) => (
              <div key={i} className="bg-gray-700 rounded p-2 text-xs">
                <span className="font-medium text-red-400">RPN: {String(m.rpn ?? "—")}</span>
                <span className="mx-2 text-gray-400">|</span>
                <span>{String(m.failure_mode ?? m.id ?? "—")}</span>
              </div>
            ))}
          </div>
        </div>
      );
    }

    return (
      <pre className="text-xs text-gray-400 bg-gray-700 p-3 rounded mt-3 overflow-auto max-h-40">
        {JSON.stringify(data, null, 2)}
      </pre>
    );
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-sm" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-gray-800 rounded-xl border border-gray-700 shadow-2xl p-6 w-[90vw] max-w-lg max-h-[90vh] overflow-y-auto">
          <Dialog.Title className="text-lg font-semibold text-gray-100 flex items-center gap-2">
            <span className="text-yellow-400">⚠</span>
            人工审批门
          </Dialog.Title>
          <Dialog.Description className="text-sm text-gray-400 mt-1">
            {gateLabels[approval.gate_type] ?? approval.gate_type} — Session:{" "}
            <span className="font-mono text-xs">{approval.session_id.slice(0, 8)}…</span>
          </Dialog.Description>

          {renderGateData()}

          {/* Reviewer fields */}
          <div className="mt-4 space-y-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1">审查人员 ID</label>
              <input
                type="text"
                value={reviewerId}
                onChange={(e) => setReviewerId(e.target.value)}
                placeholder="工号或姓名"
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">审查意见（可选）</label>
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                rows={3}
                placeholder="填写审查说明…"
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
              />
            </div>
          </div>

          {error && (
            <p className="mt-3 text-sm text-red-400">{error}</p>
          )}

          {/* Action buttons */}
          <div className="flex gap-3 mt-5 justify-end">
            <button
              onClick={() => handleDecision(false)}
              disabled={loading}
              className="px-4 py-2 rounded-lg border border-red-600 text-red-400 text-sm hover:bg-red-900/30 disabled:opacity-50 transition-colors"
            >
              拒绝 / 终止
            </button>
            <button
              onClick={() => handleDecision(true)}
              disabled={loading}
              className="px-4 py-2 rounded-lg bg-green-700 text-white text-sm hover:bg-green-600 disabled:opacity-50 transition-colors font-medium"
            >
              {loading ? "处理中…" : "确认通过"}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
