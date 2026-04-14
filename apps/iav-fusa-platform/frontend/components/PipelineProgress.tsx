"use client";

import { CheckCircle, Circle, Clock, AlertCircle } from "lucide-react";

type StageStatus = "pending" | "running" | "completed" | "waiting_approval" | "error";

interface Stage {
  id: string;
  label: string;
  description: string;
  status: StageStatus;
}

const HARA_STAGES: Omit<Stage, "status">[] = [
  { id: "parse_item_definition", label: "Item Definition", description: "解析系统边界与功能" },
  { id: "identify_failure_modes", label: "失效模式识别", description: "4关键词模板" },
  { id: "derive_hazards", label: "危害推导", description: "映射到车辆级危害" },
  { id: "estimate_seco", label: "S/E/C/O 评估", description: "风险参数量化" },
  { id: "classify_asil", label: "ASIL 定级", description: "ISO 26262 分级" },
  { id: "generate_safety_goals", label: "安全目标", description: "生成安全需求" },
];

const FMEA_STAGES: Omit<Stage, "status">[] = [
  { id: "analyze_structure", label: "结构分析", description: "系统层次分解" },
  { id: "mine_failure_modes", label: "失效模式挖掘", description: "组件级失效模式" },
  { id: "calculate_rpn", label: "RPN 计算", description: "S×O×D 风险评估" },
  { id: "recommend_actions", label: "纠正措施", description: "优化行动计划" },
];

const FTA_STAGES: Omit<Stage, "status">[] = [
  { id: "define_top_event", label: "顶事件定义", description: "不希望事件确定" },
  { id: "decompose_gates", label: "逻辑门分解", description: "AND/OR 递归分解" },
  { id: "map_basic_events", label: "底事件映射", description: "关联 FMEA 失效模式" },
  { id: "validate_logic", label: "一致性校验", description: "逻辑门完整性检查" },
];

const STAGE_TEMPLATES: Record<string, Omit<Stage, "status">[]> = {
  hara: HARA_STAGES,
  fmea: FMEA_STAGES,
  fta: FTA_STAGES,
};

interface PipelineProgressProps {
  analysisType: "hara" | "fmea" | "fta";
  currentStage?: string;
  awaitingApproval?: boolean;
}

/**
 * PipelineProgress visualises the current stage of a FuSa analysis pipeline.
 */
export function PipelineProgress({
  analysisType,
  currentStage,
  awaitingApproval,
}: PipelineProgressProps) {
  const template = STAGE_TEMPLATES[analysisType] ?? HARA_STAGES;
  const currentIdx = template.findIndex((s) => s.id === currentStage);

  const stages: Stage[] = template.map((s, idx) => {
    let status: StageStatus = "pending";
    if (idx < currentIdx) status = "completed";
    else if (idx === currentIdx) {
      status = awaitingApproval ? "waiting_approval" : "running";
    }
    return { ...s, status };
  });

  const Icon = ({ status }: { status: StageStatus }) => {
    if (status === "completed")
      return <CheckCircle className="w-5 h-5 text-green-400" />;
    if (status === "running")
      return <Clock className="w-5 h-5 text-blue-400 animate-spin" />;
    if (status === "waiting_approval")
      return <AlertCircle className="w-5 h-5 text-yellow-400" />;
    if (status === "error")
      return <AlertCircle className="w-5 h-5 text-red-400" />;
    return <Circle className="w-5 h-5 text-gray-600" />;
  };

  const labelMap: Record<string, string> = {
    hara: "HARA",
    fmea: "FMEA",
    fta: "FTA",
  };

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-200 mb-4">
        {labelMap[analysisType]} 流水线进度
      </h3>
      <ol className="relative border-l border-gray-700 ml-2.5 space-y-4">
        {stages.map((stage) => (
          <li key={stage.id} className="ml-6">
            <span className="absolute -left-3 flex items-center justify-center">
              <Icon status={stage.status} />
            </span>
            <div
              className={`text-sm font-medium ${
                stage.status === "running"
                  ? "text-blue-300"
                  : stage.status === "completed"
                  ? "text-gray-300"
                  : stage.status === "waiting_approval"
                  ? "text-yellow-300"
                  : "text-gray-500"
              }`}
            >
              {stage.label}
            </div>
            <p className="text-xs text-gray-500 mt-0.5">{stage.description}</p>
            {stage.status === "waiting_approval" && (
              <p className="text-xs text-yellow-500 mt-1 font-medium">
                ⚠ 等待人工审批…
              </p>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}
