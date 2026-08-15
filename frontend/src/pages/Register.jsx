import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Alert, Button, Card, Input } from "../components/ui";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setBusy(true);
    try {
      await register(name, email, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <Card className="w-full max-w-md p-8">
        <h1 className="text-2xl font-bold text-slate-800">Create account</h1>
        <p className="mt-1 text-sm text-slate-500">Start auditing your websites</p>
        {error ? <div className="mt-4"><Alert>{error}</Alert></div> : null}
        <form onSubmit={submit} className="mt-6 space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Name</label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Email</label>
            <Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Password</label>
            <Input type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} />
            <p className="mt-1 text-xs text-slate-400">At least 8 characters.</p>
          </div>
          <Button type="submit" className="w-full" disabled={busy}>
            {busy ? "Creating…" : "Create account"}
          </Button>
        </form>
        <p className="mt-4 text-sm text-slate-500">
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-blue-600 hover:underline">
            Sign in
          </Link>
        </p>
      </Card>
    </div>
  );
}
