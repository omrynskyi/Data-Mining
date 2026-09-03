import React, { useState, useRef, useCallback, useMemo, useEffect } from 'react';
import Map, { Marker, Source, Layer } from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';
import { Search } from 'lucide-react';

export default function MapPicker({ pickup, setPickup, dropoff, setDropoff, result }) {
  const [activeMarker, setActiveMarker] = useState('pickup');
  const [searchQuery, setSearchQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const mapRef = useRef();

  useEffect(() => {
    const delayDebounceFn = setTimeout(async () => {
      if (searchQuery.length > 2) {
        setIsSearching(true);
        try {
          // fetch max 5 suggestions
          const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&addressdetails=1&limit=5&q=${encodeURIComponent(searchQuery)}`);
          const data = await res.json();
          setSuggestions(data || []);
        } catch (err) {
          console.error(err);
        } finally {
          setIsSearching(false);
        }
      } else {
        setSuggestions([]);
      }
    }, 500); // 500ms debounce

    return () => clearTimeout(delayDebounceFn);
  }, [searchQuery]);

  const handleSelectSuggestion = (s) => {
    const lat = parseFloat(s.lat);
    const lon = parseFloat(s.lon);
    if (activeMarker === 'pickup') {
      setPickup([lat, lon]);
    } else {
      setDropoff([lat, lon]);
    }
    
    // Fly to location
    mapRef.current?.flyTo({ center: [lon, lat], zoom: 14, duration: 2000 });
    
    // Clear search and suggestions
    setSearchQuery('');
    setSuggestions([]);
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (suggestions.length > 0) {
      handleSelectSuggestion(suggestions[0]);
    }
  };

  const handleMapClick = useCallback((e) => {
    const { lat, lng } = e.lngLat;
    if (activeMarker === 'pickup') {
      setPickup([lat, lng]);
    } else {
      setDropoff([lat, lng]);
    }
  }, [activeMarker, setPickup, setDropoff]);

  // Compute GeoJSON for the line
  const routeGeoJSON = useMemo(() => {
    if (!pickup || !dropoff) return null;
    return {
      type: 'Feature',
      properties: {},
      geometry: {
        type: 'LineString',
        coordinates: [
          [pickup[1], pickup[0]],
          [dropoff[1], dropoff[0]]
        ]
      }
    };
  }, [pickup, dropoff]);

  // Compute midpoint for ETA badge
  const midpoint = useMemo(() => {
    if (!pickup || !dropoff) return null;
    return [
      (pickup[0] + dropoff[0]) / 2,
      (pickup[1] + dropoff[1]) / 2
    ];
  }, [pickup, dropoff]);

  return (
    <>
      <div className="map-search-overlay" style={{ position: 'absolute', top: '1rem', left: '50%', transform: 'translateX(-50%)', zIndex: 1001, width: '90%', maxWidth: '400px' }}>
        <div style={{ display: 'flex', gap: '0.5rem', background: 'white', padding: '0.5rem', borderRadius: '8px', boxShadow: 'var(--shadow-md)', width: '100%' }}>
          <input 
            type="text" 
            placeholder={`Search ${activeMarker} address...`}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch(e)}
            style={{ width: '100%', fontSize: '0.95rem', border: 'none', outline: 'none', padding: '0.5rem' }}
          />
          <button type="button" className="btn-primary" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }} onClick={handleSearch}>
            <Search size={18} />
          </button>
        </div>

        {/* Autocomplete Dropdown */}
        {suggestions.length > 0 && (
          <ul style={{ 
            position: 'absolute', top: '100%', left: 0, right: 0, 
            background: 'white', listStyle: 'none', margin: '0.25rem 0 0 0', padding: 0, 
            border: '1px solid var(--border-light)', borderRadius: '8px', boxShadow: 'var(--shadow-md)', 
            zIndex: 1001, maxHeight: '200px', overflowY: 'auto' 
          }}>
            {suggestions.map((s, idx) => (
              <li 
                key={idx} 
                style={{ 
                  padding: '0.75rem', 
                  borderBottom: idx < suggestions.length - 1 ? '1px solid var(--border-light)' : 'none', 
                  cursor: 'pointer', 
                  fontSize: '0.85rem',
                  color: 'var(--text-main)'
                }}
                onClick={() => handleSelectSuggestion(s)}
                onMouseEnter={(e) => e.currentTarget.style.background = 'var(--bg-main)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'white'}
              >
                {s.display_name}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div style={{ position: 'absolute', top: '5.5rem', left: '50%', transform: 'translateX(-50%)', zIndex: 1000, display: 'flex', gap: '0.5rem', background: 'white', padding: '0.5rem', borderRadius: '8px', boxShadow: 'var(--shadow-md)' }}>
        <button 
          type="button"
          className="btn-primary" 
          style={{ padding: '0.5rem 1rem', width: 'auto', background: activeMarker === 'pickup' ? 'black' : 'var(--bg-main)', color: activeMarker === 'pickup' ? 'white' : 'var(--text-main)', border: activeMarker === 'pickup' ? 'none' : '1px solid var(--border-light)' }}
          onClick={() => setActiveMarker('pickup')}
        >
          Set Pickup
        </button>
        <button 
          type="button"
          className="btn-primary" 
          style={{ padding: '0.5rem 1rem', width: 'auto', background: activeMarker === 'dropoff' ? 'var(--primary)' : 'var(--bg-main)', color: activeMarker === 'dropoff' ? 'white' : 'var(--text-main)', border: activeMarker === 'dropoff' ? 'none' : '1px solid var(--border-light)' }}
          onClick={() => setActiveMarker('dropoff')}
        >
          Set Dropoff
        </button>
      </div>

      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0 }}>
        <Map
          ref={mapRef}
          initialViewState={{
            longitude: -73.98,
            latitude: 40.75,
            zoom: 12
          }}
          mapStyle="https://tiles.openfreemap.org/styles/positron"
          style={{ width: '100%', height: '100%' }}
          onClick={handleMapClick}
        >
          {/* Draw Route Line */}
          {routeGeoJSON && (
            <Source id="route" type="geojson" data={routeGeoJSON}>
              <Layer 
                id="route-line" 
                type="line" 
                paint={{
                  'line-color': '#2563eb', // MapLibre requires exact color values, not CSS variables
                  'line-width': 4,
                  'line-dasharray': [2, 2]
                }} 
              />
            </Source>
          )}

          {pickup && (
            <Marker longitude={pickup[1]} latitude={pickup[0]} anchor="center">
              <div style={{ background: 'black', width: '14px', height: '14px', borderRadius: '50%', border: '2px solid white', boxShadow: '0 2px 4px rgba(0,0,0,0.3)', cursor: 'pointer' }}></div>
            </Marker>
          )}
          
          {dropoff && (
            <Marker longitude={dropoff[1]} latitude={dropoff[0]} anchor="center">
               <div style={{ background: 'var(--primary)', width: '14px', height: '14px', border: '2px solid white', boxShadow: '0 2px 4px rgba(0,0,0,0.3)', cursor: 'pointer' }}></div>
            </Marker>
          )}

          {/* ETA Badge in middle of the line */}
          {midpoint && result && (
            <Marker longitude={midpoint[1]} latitude={midpoint[0]} anchor="center" style={{ zIndex: 10 }}>
              <div style={{ 
                background: 'black', 
                color: 'white', 
                padding: '0.25rem 0.75rem', 
                borderRadius: '20px', 
                fontSize: '0.85rem', 
                fontWeight: 'bold',
                boxShadow: '0 4px 6px rgba(0,0,0,0.3)',
                whiteSpace: 'nowrap'
              }}>
                {Math.floor(result.predicted_duration_minutes)}m {Math.round(result.predicted_duration_seconds % 60)}s
              </div>
            </Marker>
          )}
        </Map>
      </div>
    </>
  );
}
