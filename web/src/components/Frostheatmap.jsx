import React, { useEffect, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import './FrostHeatmap.css';
import { mapToken } from './Maptoken';
import csvData from '../data/stations.json';
import { fetchFrostRisk } from '../api/frostRisk';

const STAGES = [
  { id: 'Pinkbud', label: 'Stage 1' },
  { id: 'Fullbloom', label: 'Stage 2' },
  { id: 'Petalfall', label: 'Stage 3' },
  { id: 'Fruitset', label: 'Stage 4' },
  { id: 'Smallnut', label: 'Stage 5' }
];

const FrostHeatmap = () => {
  const mapContainer = useRef(null);
  const map = useRef(null);
  const MAPBOX_TOKEN = mapToken;

  const [showHeatmap, setShowHeatmap] = useState(true);
  const [filterLevel, setFilterLevel] = useState('all');
  const [mapStyle, setMapStyle] = useState('streets-v12');
  const [selectedCrop, setSelectedCrop] = useState('almond');
  const [selectedStage, setSelectedStage] = useState('Pinkbud');
  const [rawFeatures, setRawFeatures] = useState([]);
  
  // Default date to today (California time usually preferred, but local browser time is simpler for now)
  const todayStr = new Date().toISOString().split('T')[0];
  const [selectedDate, setSelectedDate] = useState(todayStr);

  const [hoveredFeature, setHoveredFeature] = useState(null);
  const [stats, setStats] = useState({ total: 0, high: 0, medium: 0, low: 0 });
  const [geoJsonData, setGeoJsonData] = useState(null);

  const [loading, setLoading] = useState(false);

  // Central Valley station bounds
  const centralValleyBounds = {
    minLng: -121.0,
    maxLng: -118.5,
    minLat: 35.0,
    maxLat: 37.5
  };

  // Move fetchData OUTSIDE of useEffect so we can call it manually
  const fetchData = async () => {
    setLoading(true);
    
    // Filter for Central Valley stations
    const centralValleyStations = csvData.filter(station => {
      const lng = parseFloat(station.Longitude);
      const lat = parseFloat(station.Latitude);
      return (
        lng >= centralValleyBounds.minLng &&
        lng <= centralValleyBounds.maxLng &&
        lat >= centralValleyBounds.minLat &&
        lat <= centralValleyBounds.maxLat
      );
    });

    console.log(`Found ${centralValleyStations.length} Central Valley stations`);

    // Fetch frost risk for each station
    // Limit to first 10 for demo/performance, or use all if backend can handle it
    // Ideally backend should support bulk requests or bounding box queries
    const stationsToFetch = centralValleyStations.slice(0, 20); 
    
    // Use the selected date from state
    const today = selectedDate;
    
    // Fallback mock data for demo purposes if API fails or returns empty
    const generateMockData = (station) => ({
      type: 'Feature',
      properties: {
        temp: Math.floor(Math.random() * 15) - 8,
        riskLevel: Math.random() > 0.6 ? 'high' : Math.random() > 0.4 ? 'medium' : 'low',
        location: station.Name,
        county: station.County,
        elevation: station.Elevation,
        status: station.Status,
        stationId: station.ID
      },
      geometry: {
        type: 'Point',
        coordinates: [parseFloat(station.Longitude), parseFloat(station.Latitude)]
      }
    });

    const riskPromises = stationsToFetch.map(async (station) => {
      try {
        const result = await fetchFrostRisk({
          lat: parseFloat(station.Latitude),
          lon: parseFloat(station.Longitude),
          date: today,
          crop: selectedCrop,
          variety: "nonpareil",
          stationId: station.ID
        });
        
        // Enhance result with station metadata from CSV
        result.properties.county = station.County;
        result.properties.elevation = station.Elevation;
        result.properties.status = station.Status;
        result.properties.location = station.Name; // Ensure location name is set
        
        console.log(`Data source for ${station.ID}: API`, result);
        return result;
      } catch (err) {
        console.warn(`Failed to fetch risk for station ${station.ID}, using mock data:`, err);
        const mockData = generateMockData(station);
        console.log(`Data source for ${station.ID}: Mock Fallback`, mockData);
        return mockData;
      }
    });

    const results = await Promise.all(riskPromises);
    const validFeatures = results.filter(f => f !== null);

    setRawFeatures(validFeatures);
    setLoading(false);
  };

  useEffect(() => {
    if (!rawFeatures) return;

    const processedFeatures = rawFeatures.map(feature => {
      // If we have detailed stage data, recalculate risk based on selection
      let newRisk = feature.properties.riskLevel; // Default to existing
      
      // Normalize 'moderate' to 'medium' from backend if present
      if (newRisk === 'moderate') newRisk = 'medium';

      console.log("Full Feature Payload:", feature);

      if (feature.properties.crop && feature.properties.crop.stages) {
        const stageData = feature.properties.crop.stages[selectedStage];
        if (stageData) {
          const prob = stageData.probability;
          if (prob >= 0.6) newRisk = 'high';
          else if (prob >= 0.3) newRisk = 'medium';
          else newRisk = 'low';
        }
      }
      
      return {
         ...feature,
         properties: {
           ...feature.properties,
           riskLevel: newRisk
         }
      };
    });

    const geoJson = {
      type: 'FeatureCollection',
      features: processedFeatures
    };

    setGeoJsonData(geoJson);

    // Calculate statistics
    const highCount = processedFeatures.filter(f => f.properties.riskLevel === 'high').length;
    const mediumCount = processedFeatures.filter(f => f.properties.riskLevel === 'medium').length;
    const lowCount = processedFeatures.filter(f => f.properties.riskLevel === 'low').length;

    setStats({
      total: processedFeatures.length,
      high: highCount,
      medium: mediumCount,
      low: lowCount
    });

  }, [rawFeatures, selectedStage]);

  useEffect(() => {
    setGeoJsonData({ type: 'FeatureCollection', features: [] });
  }, []);

  const mapStyles = {
    'streets-v12': 'Streets',
    'satellite-v9': 'Satellite',
    'outdoors-v12': 'Outdoors',
    'light-v11': 'Light',
    'dark-v11': 'Dark'
  };

  // Calculate bounds for all stations
  const calculateBounds = (features) => {
    if (features.length === 0) return null;

    let minLng = Infinity, maxLng = -Infinity;
    let minLat = Infinity, maxLat = -Infinity;

    features.forEach(feature => {
      const [lng, lat] = feature.geometry.coordinates;
      minLng = Math.min(minLng, lng);
      maxLng = Math.max(maxLng, lng);
      minLat = Math.min(minLat, lat);
      maxLat = Math.max(maxLat, lat);
    });

    return [[minLng, minLat], [maxLng, maxLat]];
  };

  useEffect(() => {
    if (!mapContainer.current || !geoJsonData) return;
    if (map.current) return;

    mapboxgl.accessToken = MAPBOX_TOKEN;

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: `mapbox://styles/mapbox/${mapStyle}`,
      center: [-119.5, 36.5],
      zoom: 8
    });

    map.current.on('load', () => {
      // Add the data source
      if (!map.current.getSource('frost-data')) {
        map.current.addSource('frost-data', {
          type: 'geojson',
          data: geoJsonData
        });

        // Add the heatmap layer
        map.current.addLayer({
          id: 'frost-heatmap',
          type: 'heatmap',
          source: 'frost-data',
          paint: {
            'heatmap-color': [
              'interpolate',
              ['linear'],
              ['heatmap-density'],
              0, 'rgba(0, 0, 255, 0)',
              0.3, 'rgba(0, 255, 255, 0.5)',
              0.6, 'rgba(255, 255, 0, 0.5)',
              1, 'rgba(255, 0, 0, 0.8)'
            ],
            'heatmap-radius': [
              'interpolate',
              ['linear'],
              ['zoom'],
              0, 2,
              22, 20
            ],
            'heatmap-opacity': [
              'interpolate',
              ['linear'],
              ['zoom'],
              7, 1,
              9, 0.8
            ]
          }
        });

        // Add a circles layer for interactive tooltips
        map.current.addLayer({
          id: 'frost-points',
          type: 'circle',
          source: 'frost-data',
          paint: {
            'circle-radius': 8,
            'circle-color': [
              'case',
              ['==', ['get', 'riskLevel'], 'high'],
              '#FF0000',
              ['==', ['get', 'riskLevel'], 'medium'],
              '#FFFF00',
              '#0000FF'
            ],
            'circle-opacity': 0.7,
            'circle-stroke-width': 2,
            'circle-stroke-color': '#fff'
          }
        });

        // Fit map to bounds of all stations
        const bounds = calculateBounds(geoJsonData.features);
        if (bounds) {
          map.current.fitBounds(bounds, {
            padding: 50,
            duration: 1000
          });
        }

        // Hover effect
        map.current.on('mousemove', 'frost-points', (e) => {
          map.current.getCanvas().style.cursor = 'pointer';
          if (e.features.length > 0) {
            setHoveredFeature(e.features[0].properties);
          }
        });

        map.current.on('mouseleave', 'frost-points', () => {
          map.current.getCanvas().style.cursor = '';
          setHoveredFeature(null);
        });

        // Popup on click
        map.current.on('click', 'frost-points', (e) => {
          if (e.features.length > 0) {
            const properties = e.features[0].properties;
            new mapboxgl.Popup()
              .setLngLat(e.lngLat)
              .setHTML(`
                <div>
                  <strong>${properties.location}</strong><br/>
                  County: ${properties.county}<br/>
                  Elevation: ${properties.elevation}m<br/>
                  Temperature: ${properties.temp}°C<br/>
                  Risk Level: <strong>${properties.riskLevel.toUpperCase()}</strong><br/>
                  Status: ${properties.status}
                </div>
              `)
              .addTo(map.current);
          }
        });
      }
    });

    return () => {
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, [geoJsonData]);

  // Handle map style change
  useEffect(() => {
    if (map.current && map.current.isStyleLoaded()) {
      map.current.setStyle(`mapbox://styles/mapbox/${mapStyle}`);
    }
  }, [mapStyle]);

  // Handle heatmap visibility toggle
  useEffect(() => {
    if (map.current && map.current.getLayer('frost-heatmap')) {
      map.current.setLayoutProperty('frost-heatmap', 'visibility', showHeatmap ? 'visible' : 'none');
    }
  }, [showHeatmap]);

  // Handle risk level filtering
  useEffect(() => {
    if (map.current && map.current.getLayer('frost-points')) {
      if (filterLevel === 'all') {
        map.current.setFilter('frost-points', null);
      } else {
        map.current.setFilter('frost-points', ['==', ['get', 'riskLevel'], filterLevel]);
      }
    }
  }, [filterLevel]);

  const zoomToAllStations = () => {
    if (map.current && geoJsonData) {
      const bounds = calculateBounds(geoJsonData.features);
      if (bounds) {
        map.current.fitBounds(bounds, {
          padding: 50,
          duration: 1000
        });
      }
    }
  };

  if (!geoJsonData) {
    return <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Loading map...</div>;
  }

  return (
    <div style={{ display: 'flex', width: '100%', height: '100%' }}>
      {/* Sidebar */}
      <div className="sidebar">
        <div className="sidebar-section">
          <h3>CIMIS Stations</h3>
          <div className="stat">
            <span>Total Stations:</span>
            <strong>{stats.total}</strong>
          </div>
          <div className="stat">
            <span className="dot high"></span>
            <span>High Risk:</span>
            <strong>{stats.high}</strong>
          </div>
          <div className="stat">
            <span className="dot medium"></span>
            <span>Medium Risk:</span>
            <strong>{stats.medium}</strong>
          </div>
          <div className="stat">
            <span className="dot low"></span>
            <span>Low Risk:</span>
            <strong>{stats.low}</strong>
          </div>
        </div>

        <div className="sidebar-section">
          <h3>Heatmap Legend</h3>
          <div className="legend">
            <div className="legend-item">
              <div className="legend-color" style={{ background: '#FF0000' }}></div>
              <span>Very High Risk</span>
            </div>
            <div className="legend-item">
              <div className="legend-color" style={{ background: '#FFFF00' }}></div>
              <span>Medium Risk</span>
            </div>
            <div className="legend-item">
              <div className="legend-color" style={{ background: '#0000FF' }}></div>
              <span>Low Risk</span>
            </div>
          </div>
        </div>

        <div className="sidebar-section">
          <h3>Controls</h3>
          <label className="checkbox">
            <input 
              type="checkbox" 
              checked={showHeatmap} 
              onChange={(e) => setShowHeatmap(e.target.checked)}
            />
            Show Heatmap
          </label>

          <label className="filter-label">Filter by Risk:</label>
          <select 
            value={filterLevel} 
            onChange={(e) => setFilterLevel(e.target.value)}
            className="filter-select"
          >
            <option value="all">All</option>
            <option value="high">High Only</option>
            <option value="medium">Medium Only</option>
            <option value="low">Low Only</option>
          </select>

          <label className="filter-label">Crop:</label>
          <select 
            value={selectedCrop} 
            onChange={(e) => setSelectedCrop(e.target.value)}
            className="filter-select"
          >
            <option value="almond">Almond</option>
          </select>

          <label className="filter-label">Date:</label>
          <input 
            type="date" 
            value={selectedDate}
            max={todayStr} // Disables future dates
            onChange={(e) => setSelectedDate(e.target.value)}
            className="filter-select"
            style={{ padding: '5px' }}
          />

          <label className="filter-label">Stage:</label>
          <select 
            value={selectedStage} 
            onChange={(e) => setSelectedStage(e.target.value)}
            className="filter-select"
          >
            {STAGES.map(stage => (
              <option key={stage.id} value={stage.id}>{stage.label}</option>
            ))}
          </select>

          <label className="filter-label">Map Style:</label>
          <select 
            value={mapStyle} 
            onChange={(e) => setMapStyle(e.target.value)}
            className="filter-select"
          >
            {Object.entries(mapStyles).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>

          <button 
            className="region-btn"
            onClick={zoomToAllStations}
            style={{ marginTop: '10px', width: '100%' }}
          >
            Fit All Stations
          </button>

          {/* NEW BUTTON */}
          <button 
            className="region-btn"
            onClick={fetchData}
            disabled={loading}
            style={{ marginTop: '10px', width: '100%', backgroundColor: loading ? '#ccc' : '#28a745' }}
          >
            {loading ? 'Fetching Data...' : 'Fetch Risk Data'}
          </button>
        </div>

        {hoveredFeature && (
          <div className="sidebar-section hover-info">
            <h3>Station Info</h3>
            <div className="stat">
              <span>Location:</span>
              <strong>{hoveredFeature.location}</strong>
            </div>
            <div className="stat">
              <span>County:</span>
              <strong>{hoveredFeature.county}</strong>
            </div>
            <div className="stat">
              <span>Elevation:</span>
              <strong>{hoveredFeature.elevation}m</strong>
            </div>
            <div className="stat">
              <span>Temperature:</span>
              <strong>{hoveredFeature.temp}°C</strong>
            </div>
            <div className="stat">
              <span>Risk Level:</span>
              <strong style={{ color: 
                hoveredFeature.riskLevel === 'high' ? '#FF0000' :
                hoveredFeature.riskLevel === 'medium' ? '#FFFF00' : '#0000FF'
              }}>
                {hoveredFeature.riskLevel.toUpperCase()}
              </strong>
            </div>
          </div>
        )}
      </div>

      {/* Map */}
      <div ref={mapContainer} style={{ flex: 1 }} />
    </div>
  );
};

export default FrostHeatmap;