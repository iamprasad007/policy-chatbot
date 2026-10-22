import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import type { EmbedSnippet } from "../../lib/types";

export default function EmbedTab({ projectId }: { projectId: number }) {
  const [copied, setCopied] = useState(false);
  const { data } = useQuery({
    queryKey: ["embed-snippet", projectId],
    queryFn: () => api.get<EmbedSnippet>(`/api/projects/${projectId}/embed-snippet`),
  });

  if (!data) return <p className="text-slate-500">Loading...</p>;

  async function copy() {
    await navigator.clipboard.writeText(data!.snippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="max-w-2xl space-y-4">
      <p className="text-slate-600 text-sm">
        Paste this snippet before the closing <code>&lt;/body&gt;</code> tag of any website. It renders a
        floating chat button wired to this project.
      </p>
      <pre className="bg-slate-900 text-slate-100 rounded-lg p-4 text-sm overflow-x-auto">
        {data.snippet}
      </pre>
      <button onClick={copy} className="bg-slate-900 text-white rounded px-4 py-2">
        {copied ? "Copied!" : "Copy to clipboard"}
      </button>
    </div>
  );
}
