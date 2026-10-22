import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { LLM_PROVIDERS, RagConfig, RagConfigInput } from "../../lib/types";

export default function ModelTab({ projectId }: { projectId: number }) {
  const queryClient = useQueryClient();
  const { data: config } = useQuery({
    queryKey: ["rag-config", projectId],
    queryFn: () => api.get<RagConfig>(`/api/projects/${projectId}/rag-config`),
  });

  const [form, setForm] = useState<RagConfigInput | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (config && !form) {
      const { api_key_masked, ...rest } = config;
      setForm({ ...rest, api_key: "" });
    }
  }, [config, form]);

  const save = useMutation({
    mutationFn: (payload: RagConfigInput) => api.put<RagConfig>(`/api/projects/${projectId}/rag-config`, payload),
    onSuccess: (data) => {
      queryClient.setQueryData(["rag-config", projectId], data);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    },
  });

  if (!form) return <p className="text-slate-500">Loading...</p>;

  function field<K extends keyof RagConfigInput>(key: K, value: RagConfigInput[K]) {
    setForm((prev) => (prev ? { ...prev, [key]: value } : prev));
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (form) save.mutate(form);
  }

  return (
    <form onSubmit={onSubmit} className="space-y-8 max-w-2xl">
      <section className="bg-white border rounded-lg p-5 space-y-4">
        <h2 className="font-medium">Model</h2>
        <LabeledField label="Provider">
          <select
            value={form.provider}
            onChange={(e) => field("provider", e.target.value)}
            className="w-full border rounded px-3 py-2"
          >
            {LLM_PROVIDERS.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
          </select>
        </LabeledField>
        <LabeledField label="Model ID">
          <input
            value={form.model_id}
            onChange={(e) => field("model_id", e.target.value)}
            className="w-full border rounded px-3 py-2"
          />
        </LabeledField>
        <LabeledField label={config?.api_key_masked ? `API key (currently ${config.api_key_masked})` : "API key"}>
          <input
            type="password"
            placeholder="Leave blank to keep existing key"
            value={form.api_key}
            onChange={(e) => field("api_key", e.target.value)}
            className="w-full border rounded px-3 py-2"
          />
        </LabeledField>
        <div className="grid grid-cols-2 gap-4">
          <LabeledField label="Base URL (optional)">
            <input
              value={form.base_url ?? ""}
              onChange={(e) => field("base_url", e.target.value || null)}
              className="w-full border rounded px-3 py-2"
            />
          </LabeledField>
          <LabeledField label="Region (IBM watsonx)">
            <input
              value={form.region ?? ""}
              onChange={(e) => field("region", e.target.value || null)}
              className="w-full border rounded px-3 py-2"
            />
          </LabeledField>
        </div>
        {form.provider === "ibm_watsonx" && (
          <LabeledField label="IBM project ID">
            <input
              value={form.project_id_external ?? ""}
              onChange={(e) => field("project_id_external", e.target.value || null)}
              className="w-full border rounded px-3 py-2"
            />
          </LabeledField>
        )}
        <div className="grid grid-cols-2 gap-4">
          <NumberField
            label="Temperature"
            value={form.temperature}
            step={0.1}
            onChange={(v) => field("temperature", v)}
          />
          <NumberField
            label="Max new tokens"
            value={form.max_new_tokens}
            onChange={(v) => field("max_new_tokens", v)}
          />
        </div>
      </section>

      <section className="bg-white border rounded-lg p-5 space-y-4">
        <h2 className="font-medium">Retrieval</h2>
        <div className="grid grid-cols-3 gap-4">
          <NumberField label="k" value={form.search_k} onChange={(v) => field("search_k", v)} />
          <NumberField label="fetch_k" value={form.fetch_k} onChange={(v) => field("fetch_k", v)} />
          <NumberField
            label="lambda_mult"
            value={form.lambda_mult}
            step={0.1}
            onChange={(v) => field("lambda_mult", v)}
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <NumberField
            label="Chunk size"
            value={form.chunk_size}
            onChange={(v) => field("chunk_size", v)}
          />
          <NumberField
            label="Chunk overlap"
            value={form.chunk_overlap}
            onChange={(v) => field("chunk_overlap", v)}
          />
        </div>
      </section>

      <section className="bg-white border rounded-lg p-5 space-y-4">
        <h2 className="font-medium">System prompt override (optional)</h2>
        <textarea
          value={form.system_prompt ?? ""}
          onChange={(e) => field("system_prompt", e.target.value || null)}
          rows={4}
          className="w-full border rounded px-3 py-2"
        />
      </section>

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={save.isPending}
          className="bg-slate-900 text-white rounded px-5 py-2 disabled:opacity-50"
        >
          {save.isPending ? "Saving..." : "Save settings"}
        </button>
        {saved && <span className="text-sm text-green-600">Saved</span>}
        {save.isError && <span className="text-sm text-red-600">{(save.error as Error).message}</span>}
      </div>
    </form>
  );
}

function LabeledField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="block text-sm text-slate-600 mb-1">{label}</span>
      {children}
    </label>
  );
}

function NumberField({
  label,
  value,
  step = 1,
  onChange,
}: {
  label: string;
  value: number;
  step?: number;
  onChange: (v: number) => void;
}) {
  return (
    <LabeledField label={label}>
      <input
        type="number"
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full border rounded px-3 py-2"
      />
    </LabeledField>
  );
}
