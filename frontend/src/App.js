import "@/index.css";
import { BrowserRouter, Routes, Route, useParams } from "react-router-dom";
import { Layout } from "@/components/Layout";
import Dashboard from "@/pages/Dashboard";
import Portfolio from "@/pages/Portfolio";
import StockAnalysis from "@/pages/StockAnalysis";
import ScannerView from "@/pages/ScannerView";
import Evals from "@/pages/Evals";
import DataHealth from "@/pages/DataHealth";
import SettingsPage from "@/pages/Settings";

const ModePage = () => {
  const { mode } = useParams();
  return <ScannerView key={mode} lockedMode={mode} />;
};

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/stock-analysis" element={<StockAnalysis />} />
          <Route path="/scanner" element={<ScannerView />} />
          <Route path="/mode/:mode" element={<ModePage />} />
          <Route path="/evals" element={<Evals />} />
          <Route path="/data-health" element={<DataHealth />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
