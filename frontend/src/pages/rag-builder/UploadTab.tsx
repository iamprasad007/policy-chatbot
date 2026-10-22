import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import type { DocumentItem, ReloadResult } from "../../lib/types";

const ACCEPTED = ".docx,.pdf,.jpg,.jpeg,.png,.json,.yaml,.yml,.md,.txt";

export default function UploadTab({ projectId }: { projectId: number }) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [reloadResult, setReloadResult] = useState<ReloadResult | null>(null);

  const { data: documents } = useQuery({
    queryKey: ["documents", projectId],
    queryFn: () => api.get<DocumentItem[]>(`/api/projects/${projectId}/documents`),
    refetchInterval: 5000,
  });

  const upload = useMutation({
    mutationFn: (files: FileList) => {
      const formData = new FormData();
      Array.from(files).forEach((file) => formData.append("files", file));
      return api.upload<DocumentItem[]>(`/api/projects/${projectId}/documents`, formData);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents", projectId] }),
  });

  const remove = useMutation({
    mutationFn: (documentId: number) => api.delete(`/api/projects/${projectId}/documents/${documentId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents", projectId] }),
  });

  const reload = useMutation({
    mutationFn: () => api.post<ReloadResult>(`/api/projects/${projectId}/documents/reload`),
    onSuccess: (result) => {
      setReloadResult(result);
      queryClient.invalidateQueries({ queryKey: ["documents", projectId] });
    },
  });

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    if (e.dataTransfer.files.length) upload.mutate(e.dataTransfer.files);
  }

  return (
    <div className="space-y-6">
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
        className="border-2 border-dashed rounded-lg p-10 text-center cursor-pointer hover:border-slate-400 text-slate-500"
      >
        Drag &amp; drop files here, or click to browse
        <div className="text-xs mt-1">docx, pdf, jpg, png, json, yaml, md, txt</div>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={ACCEPTED}
          className="hidden"
          onChange={(e) => e.target.files && upload.mutate(e.target.files)}
        />
      </div>
      {upload.isPending && <p className="text-sm text-slate-500">Uploading...</p>}
      {upload.isError && <p className="text-sm text-red-600">{(upload.error as Error).message}</p>}

      <div className="bg-white border rounded-lg divide-y">
        {documents?.map((doc) => (
          <div key={doc.id} className="flex items-center justify-between px-4 py-3">
            <div>
              <div className="font-medium">{doc.filename}</div>
              {doc.error_message && <div className="text-xs text-red-600">{doc.error_message}</div>}
            </div>
            <div className="flex items-center gap-3">
              <StatusBadge status={doc.status} />
              <button
                onClick={() => remove.mutate(doc.id)}
                className="text-slate-400 hover:text-red-600 text-sm"
              >
                Delete
              </button>
            </div>
          </div>
        ))}
        {documents?.length === 0 && (
          <div className="px-4 py-6 text-center text-slate-500">No documents uploaded yet.</div>
        )}
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={() => reload.mutate()}
          disabled={reload.isPending}
          className="bg-slate-900 text-white rounded px-4 py-2 disabled:opacity-50"
        >
          {reload.isPending ? "Reindexing..." : "Reindex"}
        </button>
        {reloadResult && (
          <span className="text-sm text-slate-500">
            {reloadResult.indexed} indexed, {reloadResult.removed} removed
            {reloadResult.errors.length > 0 && `, ${reloadResult.errors.length} error(s)`}
          </span>
        )}
      </div>
      {reloadResult && reloadResult.errors.length > 0 && (
        <ul className="text-sm text-red-600 list-disc list-inside">
          {reloadResult.errors.map((err, i) => (
            <li key={i}>{err}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: DocumentItem["status"] }) {
  const styles: Record<DocumentItem["status"], string> = {
    indexed: "bg-green-100 text-green-700",
    pending: "bg-amber-100 text-amber-700",
    error: "bg-red-100 text-red-700",
  };
  return <span className={`text-xs px-2 py-0.5 rounded-full ${styles[status]}`}>{status}</span>;
}
