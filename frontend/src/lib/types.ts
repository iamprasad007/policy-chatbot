export interface User {
  id: number;
  email: string;
}

export interface Project {
  id: number;
  name: string;
  type: "rag" | "chatbot";
  public_widget_key: string;
  created_at: string;
}

export interface RagConfig {
  provider: string;
  api_key_masked: string | null;
  model_id: string;
  base_url: string | null;
  region: string | null;
  project_id_external: string | null;
  temperature: number;
  max_new_tokens: number;
  search_k: number;
  fetch_k: number;
  lambda_mult: number;
  chunk_size: number;
  chunk_overlap: number;
  system_prompt: string | null;
}

export interface RagConfigInput extends Omit<RagConfig, "api_key_masked"> {
  api_key?: string;
}

export interface DocumentItem {
  id: number;
  filename: string;
  status: "pending" | "indexed" | "error";
  error_message: string | null;
  indexed_at: string | null;
  created_at: string;
}

export interface ReloadResult {
  indexed: number;
  removed: number;
  errors: string[];
}

export interface ChatResponse {
  response: string;
  sources: string[];
}

export interface EmbedSnippet {
  snippet: string;
  widget_js_url: string;
  public_widget_key: string;
}

export const LLM_PROVIDERS = [
  { value: "ibm_watsonx", label: "IBM watsonx" },
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
  { value: "openai_compatible", label: "Custom (OpenAI-compatible endpoint)" },
] as const;
