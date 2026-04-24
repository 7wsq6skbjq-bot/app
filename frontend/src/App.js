import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "@/components/Layout";
import Home from "@/pages/Home";
import Services from "@/pages/Services";
import About from "@/pages/About";
import Contact from "@/pages/Contact";

function App() {
    return (
        <div className="App">
            <BrowserRouter>
                <Routes>
                    <Route element={<Layout />}>
                        <Route index element={<Home />} />
                        <Route path="/services" element={<Services />} />
                        <Route path="/a-propos" element={<About />} />
                        <Route path="/contact" element={<Contact />} />
                    </Route>
                </Routes>
            </BrowserRouter>
        </div>
    );
}

export default App;
