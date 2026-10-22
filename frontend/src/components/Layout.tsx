import { Link, Outlet } from "react-router-dom";
import { useAuth } from "../lib/auth";

export default function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b bg-white px-6 py-3 flex items-center justify-between">
        <Link to="/" className="font-semibold text-lg">
          Chatbot Builder
        </Link>
        {user && (
          <div className="flex items-center gap-4 text-sm text-slate-600">
            <span>{user.email}</span>
            <button onClick={logout} className="text-slate-500 hover:text-slate-900">
              Log out
            </button>
          </div>
        )}
      </header>
      <main className="flex-1 max-w-5xl w-full mx-auto px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}
