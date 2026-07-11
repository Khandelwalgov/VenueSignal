"use client";

import { useEffect, useState } from "react";
import { fetchVenue, fetchLevel, VenueMetadata, LevelData } from "@/lib/api";
import MapDisplay from "@/components/MapDisplay";
import DetailsPanel from "@/components/DetailsPanel";

export default function Home() {
  const [venue, setVenue] = useState<VenueMetadata | null>(null);
  const [levelData, setLevelData] = useState<LevelData | null>(null);
  const [activeLevelId, setActiveLevelId] = useState<string>("L0");
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const v = await fetchVenue("unity-stadium");
        setVenue(v);
        const l = await fetchLevel("unity-stadium", activeLevelId);
        setLevelData(l);
        setError(null);
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : "Failed to load venue data";
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [activeLevelId]);

  const handleLevelChange = (newLevelId: string) => {
    setActiveLevelId(newLevelId);
    setSelectedEntityId(null);
  };

  return (
    <div className="page-container">
      <header className="header">
        <h1 className="header-title">
          VenueSignal
          {venue?.synthetic && <span className="badge-synthetic">Synthetic Venue</span>}
        </h1>
        <div>Unity Stadium</div>
      </header>

      <main id="main-content" className="main-content">
        <aside className="panel left-panel">
          <h2>Levels</h2>
          <div role="group" aria-label="Select Level">
            {["L0", "L1", "L2"].map((lId) => (
              <button
                key={lId}
                className="level-button"
                data-active={activeLevelId === lId}
                onClick={() => handleLevelChange(lId)}
                aria-pressed={activeLevelId === lId}
              >
                Level {lId.replace("L", "")}
              </button>
            ))}
          </div>
          
          <div style={{ marginTop: "2rem" }}>
            <h3>Legend</h3>
            <div style={{ display: "flex", alignItems: "center", marginBottom: "0.5rem" }}>
              <div style={{ width: "20px", height: "4px", backgroundColor: "var(--success)", marginRight: "10px" }}></div>
              <span>Open Path</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", marginBottom: "0.5rem" }}>
              <div style={{ width: "20px", height: "4px", backgroundColor: "var(--warning)", borderStyle: "dashed", marginRight: "10px" }}></div>
              <span>Restricted Path</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", marginBottom: "0.5rem" }}>
              <div style={{ width: "20px", height: "4px", backgroundColor: "var(--danger)", borderStyle: "dotted", marginRight: "10px" }}></div>
              <span>Closed Path</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", marginBottom: "0.5rem" }}>
              <div style={{ width: "16px", height: "16px", borderRadius: "50%", backgroundColor: "var(--primary)", marginRight: "12px" }}></div>
              <span>Asset / Node</span>
            </div>
          </div>
        </aside>

        <section className="center-panel">
          <div className="map-container">
            {loading ? (
              <div>Loading map data...</div>
            ) : error ? (
              <div style={{ color: "var(--danger)" }}>{error}</div>
            ) : levelData ? (
              <MapDisplay 
                levelData={levelData} 
                selectedEntityId={selectedEntityId}
                onSelectEntity={setSelectedEntityId} 
              />
            ) : null}
          </div>
        </section>

        <aside className="panel right-panel">
          <DetailsPanel 
            entityId={selectedEntityId} 
            levelData={levelData} 
          />
        </aside>
      </main>

      <footer className="bottom-panel">
        <h3>Level Summary</h3>
        {loading ? (
          <p>Loading...</p>
        ) : levelData ? (
          <div>
            <p><strong>{levelData.level.label}</strong></p>
            <ul>
              {levelData.assets.map(a => (
                <li key={a.id}>{a.label}: <span className={`status-badge ${a.status}`}>{a.status}</span></li>
              ))}
              {levelData.zones.map(z => (
                <li key={z.id}>{z.label}: <span className={`status-badge ${z.status}`}>{z.status}</span></li>
              ))}
            </ul>
          </div>
        ) : (
          <p>No data available</p>
        )}
      </footer>
    </div>
  );
}
