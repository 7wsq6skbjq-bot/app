import { Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

const ProtectedRoute = ({ children }) => {
    const { user } = useAuth();
    if (user === null) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-[#f3f6fb]">
                <div className="tech-stamp text-[#4b5d7a]">Vérification…</div>
            </div>
        );
    }
    if (!user) return <Navigate to="/admin/login" replace />;
    return children;
};

export default ProtectedRoute;
