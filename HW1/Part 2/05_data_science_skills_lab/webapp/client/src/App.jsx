import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { SkillExplorer } from './components/SkillExplorer';
import { TitanicClassifierView } from './components/TitanicClassifierView';
import { HousePricesView } from './components/HousePricesView';
import { FraudDetectionView } from './components/FraudDetectionView';
import { EcommerceAnalyticsView } from './components/EcommerceAnalyticsView';
import { DataQualityAuditView } from './components/DataQualityAuditView';
import { TelcoChurnView } from './components/TelcoChurnView';
import { CrispDmReportModal } from './components/CrispDmReportModal';
import { api } from './utils/api';

export function App() {
  const [activeTab, setActiveTab] = useState('skills');
  const [isCrispDmOpen, setIsCrispDmOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  const [skills, setSkills] = useState([]);
  const [titanicData, setTitanicData] = useState({});
  const [houseData, setHouseData] = useState({});
  const [fraudData, setFraudData] = useState({});
  const [ecommerceData, setEcommerceData] = useState({});
  const [qualityData, setQualityData] = useState({});
  const [telcoData, setTelcoData] = useState({});

  useEffect(() => {
    async function loadData() {
      try {
        const [catRes, tRes, hRes, fRes, eRes, qRes, telRes] = await Promise.all([
          api.getSkillsCatalog(),
          api.getTitanicBenchmark(),
          api.getHousePricesBenchmark(),
          api.getFraudBenchmark(),
          api.getEcommerceBenchmark(),
          api.getDataQualityBenchmark(),
          api.getTelcoBenchmark(),
        ]);

        // Every endpoint here returns flat JSON (no {success, data} wrapper) --
        // see webapp/client/src/utils/api.js for the verified real shapes.
        setSkills(catRes.skills || []);
        setTitanicData(tRes);
        setHouseData(hRes);
        setFraudData(fRes);
        setEcommerceData(eRes);
        setQualityData(qRes);
        setTelcoData(telRes);
      } catch (err) {
        console.error('Failed to load initial benchmark data:', err);
        setLoadError(
          'Could not reach the backend at /api. Start it with: cd webapp/server && ' +
          'python -m uvicorn main:app --host 127.0.0.1 --port 8005'
        );
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const handleNavigateToBenchmark = (benchmarkKey) => {
    setActiveTab(benchmarkKey);
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenCrispDm={() => setIsCrispDmOpen(true)}
        totalSkills={skills.length || 48}
      />

      <main className="main-content">
        {loadError && (
          <div className="card" style={{ borderColor: 'var(--accent-rose)', marginBottom: '1.25rem', color: 'var(--accent-rose)' }}>
            {loadError}
          </div>
        )}
        {loading && !loadError && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', color: 'var(--text-muted)', padding: '2rem' }}>
            <span className="spinner" /> Loading real benchmark data from the backend...
          </div>
        )}

        {!loading && activeTab === 'skills' && (
          <SkillExplorer skills={skills} onNavigateToBenchmark={handleNavigateToBenchmark} />
        )}
        {!loading && activeTab === 'titanic' && <TitanicClassifierView data={titanicData} />}
        {!loading && activeTab === 'house' && <HousePricesView data={houseData} />}
        {!loading && activeTab === 'fraud' && <FraudDetectionView data={fraudData} />}
        {!loading && activeTab === 'ecommerce' && <EcommerceAnalyticsView data={ecommerceData} />}
        {!loading && activeTab === 'quality' && <DataQualityAuditView data={qualityData} />}
        {!loading && activeTab === 'telco' && <TelcoChurnView data={telcoData} />}
      </main>

      <CrispDmReportModal isOpen={isCrispDmOpen} onClose={() => setIsCrispDmOpen(false)} />
    </div>
  );
}

export default App;
