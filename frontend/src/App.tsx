import { useState, useEffect, useCallback, useRef } from "react";
import GraphPane from "./components/GraphPane";
import ChatSidebar from "./components/ChatSidebar";
import Breadcrumb from "./components/Breadcrumb";
import type { GraphData, NodeData } from "./types";
import LandingPage from "./components/LandingPage";
import "./App.css";

const API_BASE = "/api";

export default function App() {
  const [showLanding, setShowLanding] = useState(true);
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState<NodeData | null>(null);
  const [highlightIds, setHighlightIds] = useState<string[]>([]);

  const [sidebarWidth, setSidebarWidth] = useState(320);
  const isResizing = useRef(false);

  const startResizing = useCallback((e: React.MouseEvent) => {
    isResizing.current = true;
    document.body.style.cursor = "col-resize";
    e.preventDefault();
  }, []);

  useEffect(() => {
    const stopResizing = () => {
      isResizing.current = false;
      document.body.style.cursor = "default";
    };
    const resize = (e: MouseEvent) => {
      if (isResizing.current) {
        const newWidth = window.innerWidth - e.clientX;
        if (newWidth > 250 && newWidth < 800) {
          setSidebarWidth(newWidth);
        }
      }
    };
    window.addEventListener("mousemove", resize);
    window.addEventListener("mouseup", stopResizing);
    return () => {
      window.removeEventListener("mousemove", resize);
      window.removeEventListener("mouseup", stopResizing);
    };
  }, []);

  const fetchGraph = useCallback(async (entity?: string, id?: string) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (entity) params.set("focus_entity", entity);
      if (id) params.set("focus_id", id);
      const res = await fetch(`${API_BASE}/graph?${params}`);
      const data = await res.json();
      setGraphData(data);
    } catch (e) {
      console.error(e);
      setGraphData({ nodes: [], edges: [] });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  const onQueryResult = useCallback((ids: string[]) => {
    setHighlightIds(ids);
  }, []);

  if (showLanding) {
    return <LandingPage onExplore={() => setShowLanding(false)} />;
  }

  return (
    <div className="app-layout">
      <header className="header">
        <Breadcrumb 
          items={["Mapping", "Graph Visualization"]} 
          onBack={() => setShowLanding(true)}
        />
      </header>
      <main className="main">
        <section className="graph-section">
          <GraphPane
            data={graphData}
            loading={loading}
            selectedNode={selectedNode}
            onSelectNode={setSelectedNode}
            highlightIds={highlightIds}
          />
        </section>
        <div className="resizer" onMouseDown={startResizing} />
        <aside
          className="chat-section"
          style={{
            width: `${sidebarWidth}px`,
            flexBasis: `${sidebarWidth}px`,
            flexGrow: 0,
            flexShrink: 0
          }}
        >
          <ChatSidebar
            onQueryResult={onQueryResult}
            graphData={graphData}
          />
        </aside>
      </main>
    </div>
  );
}
