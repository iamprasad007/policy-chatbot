import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import type { Project } from "../lib/types";

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const [creating, setCreating] = useState<"rag" | "chatbot" | null>(null);
  const [name, setName] = useState("");

  const { data: projects, isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.get<Project[]>("/api/projects"),
  });

  const createProject = useMutation({
    mutationFn: (payload: { name: string; type: "rag" | "chatbot" }) =>
      api.post<Project>("/api/projects", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setCreating(null);
      setName("");
    },
  });

  const deleteProject = useMutation({
    mutationFn: (id: number) => api.delete(`/api/projects/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["projects"] }),
  });

  function projectHref(project: Project) {
    return project.type === "rag" ? `/projects/${project.id}` : `/projects/${project.id}/chatbot`;
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-6">Your projects</h1>

      <div className="grid grid-cols-2 gap-4 mb-8">
        <button
          onClick={() => setCreating("chatbot")}
          className="border-2 border-dashed rounded-lg p-6 text-left hover:border-slate-400 transition"
        >
          <div className="font-medium">Build Chatbot</div>
          <div className="text-sm text-slate-500 mt-1">
            Flows, steps, extensions, and linking to a RAG project. Coming in a future phase.
          </div>
        </button>
        <button
          onClick={() => setCreating("rag")}
          className="border-2 border-dashed rounded-lg p-6 text-left hover:border-slate-400 transition"
        >
          <div className="font-medium">Build RAG</div>
          <div className="text-sm text-slate-500 mt-1">
            Upload documents, tune retrieval and model settings, and embed a Q&amp;A widget.
          </div>
        </button>
      </div>

      {creating && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (name.trim()) createProject.mutate({ name: name.trim(), type: creating });
          }}
          className="mb-8 flex gap-2 items-center bg-white border rounded-lg p-4"
        >
          <span className="text-sm text-slate-500">
            New {creating === "rag" ? "RAG" : "chatbot"} project:
          </span>
          <input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Project name"
            className="border rounded px-3 py-1.5 flex-1"
          />
          <button type="submit" className="bg-slate-900 text-white rounded px-4 py-1.5">
            Create
          </button>
          <button type="button" onClick={() => setCreating(null)} className="text-slate-500 px-2">
            Cancel
          </button>
        </form>
      )}

      {isLoading && <p className="text-slate-500">Loading...</p>}

      <div className="space-y-2">
        {projects?.map((project) => (
          <div
            key={project.id}
            className="flex items-center justify-between bg-white border rounded-lg px-4 py-3"
          >
            <Link to={projectHref(project)} className="flex-1">
              <div className="font-medium">{project.name}</div>
              <div className="text-xs text-slate-500 uppercase tracking-wide">{project.type}</div>
            </Link>
            <button
              onClick={() => {
                if (confirm(`Delete "${project.name}"? This cannot be undone.`)) {
                  deleteProject.mutate(project.id);
                }
              }}
              className="text-slate-400 hover:text-red-600 text-sm"
            >
              Delete
            </button>
          </div>
        ))}
        {projects?.length === 0 && <p className="text-slate-500">No projects yet — create one above.</p>}
      </div>
    </div>
  );
}
