import { useState, useEffect } from 'react';
import { Routes, Route, NavLink } from 'react-router-dom';
import MapPicker from './components/MapPicker';
import Analytics from './components/Analytics';
import Report from './pages/Report';
import './index.css';
import { MapPin, Navigation, Info } from 'lucide-react';

function PredictionDashboard() {
  const [pickup, setPickup] = useState([40.75, -73.98]);
  const [dropoff, setDropoff] = useState([40.80, -73.95]);
  const [passengerCount, setPassengerCount] = useState(1);
  const [pickupDatetime, setPickupDatetime] = useState(new Date().toISOString().slice(0, 16));

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchPrediction = async () => {
      if (!pickup || !dropoff) return;

      setLoading(true);
      setError('');

      try {
        const response = await fetch('http://localhost:8000/predict', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            pickup_latitude: pickup[0],
            pickup_longitude: pickup[1],
            dropoff_latitude: dropoff[0],
            dropoff_longitude: dropoff[1],
            passenger_count: parseInt(passengerCount, 10),
            pickup_datetime: pickupDatetime + ':00.000Z',
          }),
        });

        if (!response.ok) throw new Error('Prediction request failed');

        const data = await response.json();
        setResult(data);
      } catch (err) {
        setError(err.message || 'An error occurred.');
      } finally {
        setLoading(false);
      }
    };

    fetchPrediction();
  }, [pickup, dropoff, passengerCount, pickupDatetime]);

  return (
    <div className="app-layout">
      {/* Sidebar Area */}
      <div className="sidebar">
        <div className="sidebar-header">
          <h1>Taxi ETA</h1>
          <p>Predict your NYC trip duration instantly.</p>
          <div className="navbar">
            <NavLink to="/" className={({isActive}) => isActive ? "nav-link active" : "nav-link"}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Navigation size={16} /> Book
              </div>
            </NavLink>
            <NavLink to="/report" className={({isActive}) => isActive ? "nav-link active" : "nav-link"}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Info size={16} /> Report
              </div>
            </NavLink>
          </div>
        </div>

        <div className="sidebar-content">
          <form onSubmit={(e) => e.preventDefault()}>
            <div className="form-group">
              <label>Passenger Count</label>
              <input type="number" min="1" max="6" name="passenger_count" value={passengerCount} onChange={(e) => setPassengerCount(e.target.value)} required />
            </div>
            <div className="form-group">
              <label>Pickup Date & Time</label>
              <input type="datetime-local" name="pickup_datetime" value={pickupDatetime} onChange={(e) => setPickupDatetime(e.target.value)} required />
            </div>
            
            {/* Display coordinates as read-only */}
            <div className="form-group" style={{ opacity: 0.6 }}>
              <label>Pickup Location</label>
              <input type="text" readOnly value={`${pickup[0].toFixed(4)}, ${pickup[1].toFixed(4)}`} />
            </div>
            <div className="form-group" style={{ opacity: 0.6 }}>
              <label>Dropoff Location</label>
              <input type="text" readOnly value={`${dropoff[0].toFixed(4)}, ${dropoff[1].toFixed(4)}`} />
            </div>
          </form>

          {error && <div style={{ color: '#ef4444', marginTop: '1rem', textAlign: 'center', fontWeight: '500' }}>{error}</div>}

          {result && (
            <div className="result-container">
              <div className="result-title">Estimated Time</div>
              <div className="result-value">
                {Math.floor(result.predicted_duration_minutes)}m {Math.round(result.predicted_duration_seconds % 60)}s
              </div>
              <div className="result-subtext">{(result.predicted_duration_seconds / 60).toFixed(1)} mins total</div>
            </div>
          )}

          {/* Mini Analytics inside sidebar */}
          <div style={{ marginTop: '3rem' }}>
            <h3 style={{ fontSize: '1rem', color: 'var(--text-main)', marginBottom: '1rem' }}>Model Insights</h3>
            <Analytics />
          </div>
        </div>
      </div>

      {/* Main Map Area */}
      <div className="map-area">
        <MapPicker 
          pickup={pickup} setPickup={setPickup} 
          dropoff={dropoff} setDropoff={setDropoff}
          result={result}
        />
      </div>
    </div>
  );
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<PredictionDashboard />} />
      <Route path="/report" element={<Report />} />
    </Routes>
  );
}

export default App;
