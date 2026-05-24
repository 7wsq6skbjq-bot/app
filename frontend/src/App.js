import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "@/components/Layout";
import Home from "@/pages/Home";
import Services from "@/pages/Services";
import About from "@/pages/About";
import Contact from "@/pages/Contact";
import Galerie from "@/pages/Galerie";
import Catalogue from "@/pages/Catalogue";
import Legal from "@/pages/Legal";
import AdminLogin from "@/pages/AdminLogin";
import AdminDashboard from "@/pages/AdminDashboard";
import AdminErp from "@/pages/AdminErp";
import AdminPrintInvoice from "@/pages/erp/AdminPrintInvoice";
import AdminPrintPurchaseOrder from "@/pages/erp/AdminPrintPurchaseOrder";
import AdminPrintBol from "@/pages/erp/AdminPrintBol";
import ProtectedRoute from "@/components/ProtectedRoute";
import PwaInstallPrompt from "@/components/PwaInstallPrompt";
import { AuthProvider } from "@/context/AuthContext";

function App() {
    return (
        <div className="App">
            <BrowserRouter>
                <AuthProvider>
                    <PwaInstallPrompt />
                    <Routes>
                        {/* Public site */}
                        <Route element={<Layout />}>
                            <Route index element={<Home />} />
                            <Route path="/services" element={<Services />} />
                            <Route path="/a-propos" element={<About />} />
                            <Route path="/contact" element={<Contact />} />
                            <Route path="/galerie" element={<Navigate to="/galerie/interventions" replace />} />
                            <Route path="/galerie/:category" element={<Galerie />} />
                            <Route path="/catalogue" element={<Catalogue />} />
                            <Route path="/mentions-legales" element={<Legal />} />
                        </Route>

                        {/* Admin (no public layout) */}
                        <Route path="/admin/login" element={<AdminLogin />} />
                        <Route
                            path="/admin"
                            element={
                                <ProtectedRoute>
                                    <AdminDashboard />
                                </ProtectedRoute>
                            }
                        />
                        <Route
                            path="/admin/gestion/:tab?"
                            element={
                                <ProtectedRoute>
                                    <AdminErp />
                                </ProtectedRoute>
                            }
                        />
                        <Route
                            path="/admin/imprimer/facture/:id"
                            element={
                                <ProtectedRoute>
                                    <AdminPrintInvoice />
                                </ProtectedRoute>
                            }
                        />
                        <Route
                            path="/admin/imprimer/bon-commande/:id"
                            element={
                                <ProtectedRoute>
                                    <AdminPrintPurchaseOrder />
                                </ProtectedRoute>
                            }
                        />
                        <Route
                            path="/admin/imprimer/connaissement/:id"
                            element={
                                <ProtectedRoute>
                                    <AdminPrintBol />
                                </ProtectedRoute>
                            }
                        />
                    </Routes>
                </AuthProvider>
            </BrowserRouter>
        </div>
    );
}

export default App;
