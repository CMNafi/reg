import { Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import FirmProfile from "./pages/FirmProfile";
import Comparison from "./pages/Comparison";
import StatusBar from "./components/StatusBar";

export default function App() {
  return (
    <div className="min-h-screen pb-10">
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/firm/:crd" element={<FirmProfile />} />
        <Route path="/compare" element={<Comparison />} />
      </Routes>
      <StatusBar />
    </div>
  );
}
