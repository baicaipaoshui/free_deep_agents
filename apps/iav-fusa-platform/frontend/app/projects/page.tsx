"use client";

import { useState } from "react";
import useSWR, { mutate } from "swr";
import Link from "next/link";
import { Plus, Trash2, ChevronRight } from "lucide-react";
import { api, Project, ProjectCreate } from "@/lib/api";

const fetcher = () => api.projects.list();

export default function ProjectsPage() {
  const { data: projects, isLoading } = useSWR<Project[]>("/api/projects", fetcher);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<ProjectCreate>({
    name: "",
    description: "",
    vehicle_system: "",
    iso_standard: "ISO 26262:2018",
  });

  const handleCreate = async () => {
    await api.projects.create(form);
    await mutate("/api/projects");
    setShowForm(false);
    setForm({ name: "", description: "", vehicle_system: "", iso_standard: "ISO 26262:2018" });
  };

  const handleDelete = async (id: string) => {
    if (!confirm("确认删除此项目？")) return;
    await api.projects.delete(id);
    await mutate("/api/projects");
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold">功能安全项目</h1>
            <p className="text-gray-400 text-sm mt-1">管理 HARA / FMEA / FTA 分析项目</p>
          </div>
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            <Plus className="w-4 h-4" />
            新建项目
          </button>
        </div>

        {/* Create form */}
        {showForm && (
          <div className="bg-gray-800 rounded-xl p-6 mb-6 border border-gray-700">
            <h2 className="text-lg font-semibold mb-4">新建项目</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-gray-400 mb-1">项目名称 *</label>
                <input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                  placeholder="如：EPS 功能安全开发"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">车辆系统 *</label>
                <input
                  value={form.vehicle_system}
                  onChange={(e) => setForm({ ...form, vehicle_system: e.target.value })}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                  placeholder="如：电动助力转向系统"
                />
              </div>
              <div className="col-span-2">
                <label className="block text-xs text-gray-400 mb-1">描述</label>
                <input
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                  placeholder="可选描述"
                />
              </div>
            </div>
            <div className="flex gap-3 mt-4 justify-end">
              <button onClick={() => setShowForm(false)} className="text-sm text-gray-400 hover:text-gray-200 px-4 py-2">
                取消
              </button>
              <button
                onClick={handleCreate}
                disabled={!form.name || !form.vehicle_system}
                className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-sm px-4 py-2 rounded-lg transition-colors"
              >
                创建
              </button>
            </div>
          </div>
        )}

        {/* Project list */}
        {isLoading ? (
          <p className="text-gray-500">加载中…</p>
        ) : projects?.length === 0 ? (
          <p className="text-gray-500 text-center py-16">暂无项目，点击"新建项目"开始</p>
        ) : (
          <div className="space-y-3">
            {projects?.map((p) => (
              <div key={p.id} className="bg-gray-800 rounded-xl border border-gray-700 p-5 flex items-center justify-between hover:border-gray-600 transition-colors group">
                <div>
                  <Link href={`/analysis/${p.id}`} className="text-base font-semibold hover:text-blue-300 transition-colors flex items-center gap-1">
                    {p.name}
                    <ChevronRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </Link>
                  <p className="text-sm text-gray-400 mt-1">{p.vehicle_system}</p>
                  <p className="text-xs text-gray-600 mt-1">
                    {p.analysis_count} 次分析 · {p.iso_standard}
                  </p>
                </div>
                <button
                  onClick={() => handleDelete(p.id)}
                  className="text-gray-600 hover:text-red-400 transition-colors p-2"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
