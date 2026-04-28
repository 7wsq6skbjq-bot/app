import {
    createContext,
    useCallback,
    useContext,
    useEffect,
    useMemo,
    useRef,
    useState,
} from "react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Axios instance. `withCredentials: true` ensures the httpOnly
// `access_token` cookie set by the backend is sent on every request.
// No tokens are stored client-side (no localStorage) — protects against XSS.
const http = axios.create({
    baseURL: API,
    withCredentials: true,
});

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    // null = checking, object = logged in, false = not logged
    const [user, setUser] = useState(null);
    const [error, setError] = useState("");

    // Bumped every time the session "state of truth" changes (login/logout).
    // fetchMe() captures the current version before making its network call
    // and skips setUser() if the version changed while it was waiting —
    // preventing a late-returning /auth/me from overwriting a fresh login.
    const sessionVersionRef = useRef(0);

    const fetchMe = useCallback(async () => {
        const version = sessionVersionRef.current;
        try {
            const { data } = await http.get("/auth/me");
            if (sessionVersionRef.current === version) {
                setUser(data);
            }
        } catch {
            // 401 is the normal "not logged in" path. Any other failure
            // (network, 5xx) is also silently treated as "not logged in".
            if (sessionVersionRef.current === version) {
                setUser(false);
            }
        }
    }, []);

    useEffect(() => {
        fetchMe();
    }, [fetchMe]);

    const login = useCallback(async (username, password) => {
        setError("");
        try {
            const { data } = await http.post("/auth/login", {
                username,
                password,
            });
            // httpOnly cookie is set by the backend (Set-Cookie header).
            sessionVersionRef.current += 1;
            setUser({ username: data.username, role: data.role });
            return true;
        } catch (err) {
            const detail = err?.response?.data?.detail;
            setError(
                typeof detail === "string"
                    ? detail
                    : "Échec de la connexion. Vérifiez vos identifiants.",
            );
            return false;
        }
    }, []);

    const logout = useCallback(async () => {
        try {
            await http.post("/auth/logout");
        } catch {
            // Even if the logout request fails, we clear client-side state.
        }
        sessionVersionRef.current += 1;
        setUser(false);
    }, []);

    const value = useMemo(
        () => ({ user, error, login, logout, http }),
        [user, error, login, logout],
    );

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error("useAuth must be used within AuthProvider");
    return ctx;
};
