"use client";

/**
 * Knowledge page: embeds the Dify knowledge base management UI via iframe.
 * Direct knowledge base operations (upload, indexing) are done in Dify.
 */
export default function KnowledgePage() {
  const difyUrl = process.env.NEXT_PUBLIC_DIFY_URL ?? "http://localhost:3001";

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col">
      <header className="border-b border-gray-800 px-8 py-4">
        <h1 className="text-xl font-bold">知识库管理</h1>
        <p className="text-gray-500 text-sm mt-1">
          管理 ISO 26262、失效模式库、历史案例等 RAG 知识库（由 Dify 提供）
        </p>
      </header>

      <div className="p-6 flex-1 flex flex-col gap-4">
        {/* Quick reference */}
        <div className="grid grid-cols-3 gap-4">
          {[
            { name: "iso26262_hara", label: "HARA 知识库", desc: "ISO 26262 Part 3 + HARA 案例" },
            { name: "iso26262_fmea", label: "FMEA 知识库", desc: "ISO 26262 Part 5 + FMEA 模板" },
            { name: "iso26262_fta", label: "FTA 知识库", desc: "ISO 26262 Part 9 + FTA 方法论" },
            { name: "failure_modes", label: "失效模式库", desc: "按子系统分类的失效模式" },
            { name: "historical_cases", label: "历史案例库", desc: "已完成的安全分析案例" },
            { name: "company_standards", label: "企业标准库", desc: "内部检查表和开发指南" },
          ].map((kb) => (
            <div
              key={kb.name}
              className="bg-gray-800 rounded-xl border border-gray-700 p-4"
            >
              <h3 className="text-sm font-semibold text-gray-200">{kb.label}</h3>
              <p className="text-xs text-gray-500 mt-1">{kb.desc}</p>
              <p className="text-xs font-mono text-gray-600 mt-2">{kb.name}</p>
            </div>
          ))}
        </div>

        {/* Dify embed */}
        <div className="flex-1 bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
          <div className="border-b border-gray-700 px-4 py-2 flex items-center justify-between">
            <span className="text-sm text-gray-400">Dify 知识库控制台</span>
            <a
              href={difyUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-blue-400 hover:text-blue-300"
            >
              在新标签页打开 ↗
            </a>
          </div>
          <iframe
            src={difyUrl}
            className="w-full h-full min-h-96"
            title="Dify Knowledge Base"
          />
        </div>
      </div>
    </div>
  );
}
