import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Alert, Button, Card, Input } from "../components/ui";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(email, password);
      navigate(location.state?.from?.pathname || "/", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <Card className="w-full max-w-md p-8">
        <h1 className="text-2xl font-bold text-slate-800">Sign in</h1>
        <p className="mt-1 text-sm text-slate-500">Universal AI SEO Platform</p>
        {error ? <div className="mt-4"><Alert>{error}</Alert></div> : null}
        <form onSubmit={submit} className="mt-6 space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Email</label>
            <Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Password</label>
            <Input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          <Button type="submit" className="w-full" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </Button>
        </form>
        <p className="mt-4 text-sm text-slate-500">
          No account?{" "}
          <Link to="/register" className="font-medium text-blue-600 hover:underline">
            Create one
          </Link>
        </p>
      </Card>
    </div>
  );
}
