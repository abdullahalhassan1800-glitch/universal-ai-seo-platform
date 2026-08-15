import { createContext, useContext, useEffect, useState } from "react";
import { api } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => JSON.parse(localStorage.getItem("user") || "null"));
  const [token, setToken] = useState(() => localStorage.getItem("token") || "");
  const [workspace, setWorkspace] = useState(() => JSON.parse(localStorage.getItem("workspace") || "null"));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const init = async () => {
      const t = localStorage.getItem("token");
      if (t) {
        try {
          const me = await api.get("/api/auth/me");
          setUser(me.user);
          setWorkspace(me.workspace);
        } catch {
          /* ignore, will redirect to login */
        }
      }
      setLoading(false);
    };
    init();
  }, []);

  const saveAuth = (data) => {
    localStorage.setItem("token", data.token);
    localStorage.setItem("user", JSON.stringify(data.user));
    localStorage.setItem("workspace", JSON.stringify(data.workspace));
    setToken(data.token);
    setUser(data.user);
    setWorkspace(data.workspace);
  };

  const login = async (email, password) => {
    const data = await api.post("/api/auth/login", { email, password });
    saveAuth(data);
  };

  const register = async (name, email, password) => {
    const data = await api.post("/api/auth/register", { name, email, password });
    saveAuth(data);
  };

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    localStorage.removeItem("workspace");
    setToken("");
    setUser(null);
    setWorkspace(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, workspace, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
