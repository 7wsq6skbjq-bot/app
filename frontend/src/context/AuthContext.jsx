import {
    createContext,
    useCallback,
    useContext,
    useEffect,
    useMemo,
    useState,
} from "react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const http = axios.create({
    baseURL: API,
    withCredentials: true,
});

http.interceptors.request.use((config) => {
    const token = localStorage.getItem("portech_admin_token");
    if (token) {
        config.headers = config.headers || {};
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null); // null = checking, object = logged in, false = not logged
    const [error, setError] = useState("");

    const fetchMe = useCallback(async () => {
        try {
            const { data } = await http.get("/auth/me");
            setUser(data);
        } catch {
            setUser(false);
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
            if (data?.access_token) {
                localStorage.setItem("portech_admin_token", data.access_token);
            }
            setUser({ username: data.username, role: data.role });
            return true;
        } catch (e) {
            const detail = e?.response?.data?.detail;
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
            /* noop */
        }
        localStorage.removeItem("portech_admin_token");
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
