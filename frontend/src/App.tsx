import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import DashboardPage from "./pages/DashboardPage";
import ChatbotPlaceholderPage from "./pages/ChatbotPlaceholderPage";
import RagBuilderPage from "./pages/rag-builder/RagBuilderPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/projects/:projectId" element={<RagBuilderPage />} />
          <Route path="/projects/:projectId/chatbot" element={<ChatbotPlaceholderPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
