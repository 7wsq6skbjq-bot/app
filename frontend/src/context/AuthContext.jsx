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
const TOKEN_KEY = "portech_access_token";

/**
 * Read/write of the access token. We use `sessionStorage` so the token dies
 * when the tab is closed — more secure than localStorage and good enough for
 * an admin console. The token is ALSO set as an httpOnly cookie by the
 * backend; the Authorization header is our reliable fallback when a browser
 * rejects/strips the cookie (Safari ITP, strict privacy settings, etc.).
 */
const getStoredToken = () => {
    try {
        return window.sessionStorage.getItem(TOKEN_KEY) || "";
    } catch {
        return "";
    }
};
const setStoredToken = (t) => {
    try {
        if (t) window.sessionStorage.setItem(TOKEN_KEY, t);
        else window.sessionStorage.removeItem(TOKEN_KEY);
    } catch {
        // sessionStorage unavailable (SSR, strict modes) — just fall back to cookie
    }
};

// Axios instance. We do NOT use `withCredentials` because:
//   1. In cross-origin production (frontend on portech.info, backend on
//      emergent.host) the deployed backend returns `Access-Control-Allow-Origin: *`
//      together with `Access-Control-Allow-Credentials: true` — which modern
//      browsers reject as a CORS violation, causing intermittent login failures.
//   2. We already authenticate via `Authorization: Bearer <token>` from the
//      sessionStorage set after login — no cookies needed.
const http = axios.create({
    baseURL: API,
    withCredentials: false,
});

// Attach Bearer token on every outgoing request if we have one in session.
http.interceptors.request.use((config) => {
    const tok = getStoredToken();
    if (tok) {
        config.headers = config.headers || {};
        config.headers.Authorization = `Bearer ${tok}`;
    }
    return config;
});

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    // null = checking, object = logged in, false = not logged
    const [user, setUser] = useState(null);
    const [error, setError] = useState("");

    // Bumped every time the session "state of truth" changes (login/logout).
    // fetchMe() captures the current version before its network call and
    // skips setUser() if the version changed while it was in flight —
    // preventing a late-returning /auth/me from overwriting a fresh login.
    const sessionVersionRef = useRef(0);

    const fetchMe = useCallback(async () => {
        const version = sessionVersionRef.current;
        // Fast path: no token stored → not logged in, skip the network call.
        if (!getStoredToken()) {
            // We still hit /auth/me once in case an httpOnly cookie exists
            // from a previous session — otherwise fall through to setUser(false).
        }
        try {
            const { data } = await http.get("/auth/me");
            if (sessionVersionRef.current === version) {
                setUser(data);
            }
        } catch {
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
            // Store the token as a Bearer fallback. The backend ALSO sets
            // an httpOnly cookie, but storing here protects us against
            // browsers that silently reject 3rd-party cookies.
            if (data.access_token) {
                setStoredToken(data.access_token);
            }
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
        setStoredToken("");
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
