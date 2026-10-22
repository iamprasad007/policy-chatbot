import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import type { Project } from "../../lib/types";
import UploadTab from "./UploadTab";
import ModelTab from "./ModelTab";
import TestTab from "./TestTab";
import EmbedTab from "./EmbedTab";

const TABS = ["Upload", "Model & Retrieval", "Test", "Embed"] as const;
type Tab = (typeof TABS)[number];

export default function RagBuilderPage() {
  const { projectId } = useParams();
  const id = Number(projectId);
  const [tab, setTab] = useState<Tab>("Upload");

  const { data: project } = useQuery({
    queryKey: ["project", id],
    queryFn: () => api.get<Project>(`/api/projects/${id}`),
  });

  return (
    <div>
      <Link to="/" className="text-sm text-slate-500 hover:text-slate-900">
        &larr; Projects
      </Link>
      <h1 className="text-2xl font-semibold mt-2 mb-6">{project?.name ?? "..."}</h1>

      <div className="flex gap-1 border-b mb-6">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm border-b-2 -mb-px ${
              tab === t ? "border-slate-900 font-medium" : "border-transparent text-slate-500"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "Upload" && <UploadTab projectId={id} />}
      {tab === "Model & Retrieval" && <ModelTab projectId={id} />}
      {tab === "Test" && <TestTab projectId={id} />}
      {tab === "Embed" && <EmbedTab projectId={id} />}
    </div>
  );
}
