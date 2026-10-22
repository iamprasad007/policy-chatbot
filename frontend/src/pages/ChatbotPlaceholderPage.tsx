import { Link } from "react-router-dom";

export default function ChatbotPlaceholderPage() {
  return (
    <div className="max-w-lg mx-auto mt-16 text-center bg-white border rounded-lg p-10">
      <h1 className="text-xl font-semibold mb-2">Flow builder coming soon</h1>
      <p className="text-slate-500 mb-6">
        The visual flow/step chatbot builder — extensions, conditions, and linking to a RAG
        project — is planned for the next phase.
      </p>
      <Link to="/" className="text-slate-900 underline">
        Back to projects
      </Link>
    </div>
  );
}
