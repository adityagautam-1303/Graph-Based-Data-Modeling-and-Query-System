import { useRef, useEffect, useCallback, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import type { GraphData, NodeData } from "../types";

interface GraphPaneProps {
  data: GraphData;
  loading: boolean;
  selectedNode: NodeData | null;
  onSelectNode: (node: NodeData | null) => void;
  highlightIds: string[];
}

const entityColors: Record<string, string> = {
  "Sales Order": "#3b82f6",
  "Delivery": "#8b5cf6",
  "Billing Document": "#059669",
  "Journal Entry": "#d97706",
  "Customer": "#ef4444",
  "Product": "#ec4899",
  "Plant": "#64748b",
};

export default function GraphPane({
  data,
  loading,
  selectedNode,
  onSelectNode,
  highlightIds,
}: GraphPaneProps) {
  const fgRef = useRef<any>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [hasZoomedToFit, setHasZoomedToFit] = useState(false);
  const observer = useRef<ResizeObserver | null>(null);
  const containerRef = useCallback((node: HTMLDivElement | null) => {
    if (observer.current) {
      observer.current.disconnect();
      observer.current = null;
    }
    if (node) {
      // Set initial dimensions
      const rect = node.getBoundingClientRect();
      setDimensions({ width: rect.width, height: rect.height });

      observer.current = new ResizeObserver((entries) => {
        for (let entry of entries) {
          const { width, height } = entry.contentRect;
          if (width > 0 && height > 0) {
            setDimensions({ width, height });
          }
        }
      });
      observer.current.observe(node);
    }
  }, []);

  useEffect(() => {
    return () => {
      if (observer.current) observer.current.disconnect();
    };
  }, []);

  const graph = {
    nodes: data.nodes.map((n) => ({
      ...n,
      val: highlightIds.includes(n.id) ? 8 : 4,
    })),
    links: data.edges.map((e) => ({ ...e, source: e.source, target: e.target })),
  };

  const handleNodeClick = useCallback(
    (node: any) => {
      onSelectNode(node as NodeData);
    },
    [onSelectNode]
  );

  const handleBackgroundClick = useCallback(() => {
    onSelectNode(null);
  }, [onSelectNode]);

  useEffect(() => {
    if (fgRef.current && selectedNode && (selectedNode as any).x !== undefined) {
      const sn = selectedNode as any;
      fgRef.current.centerAt(sn.x, sn.y, 500);
      fgRef.current.zoom(2.0, 400);
    }
  }, [selectedNode]);

  // Zoom to fit the entire massive graph when it first finishes loading
  useEffect(() => {
    setHasZoomedToFit(false);
  }, [data]);

  useEffect(() => {
    if (!fgRef.current || data.nodes.length === 0 || hasZoomedToFit) return;

    const safeWidth = Math.max(dimensions.width, 100);

    const timer = window.setTimeout(() => {
      fgRef.current?.zoomToFit(Math.min(safeWidth, 1800), 20);
      setHasZoomedToFit(true);
    }, 150);

    return () => window.clearTimeout(timer);
  }, [data, dimensions, hasZoomedToFit]);

  if (loading) {
    return (
      <div className="graph-pane loading">
        <div className="spinner" />
        <p>Loading graph...</p>
      </div>
    );
  }

  return (
    <div className="graph-pane" ref={containerRef}>

      <ForceGraph2D
        ref={fgRef}
        width={dimensions.width}
        height={dimensions.height}
        graphData={graph}
        onNodeClick={handleNodeClick}
        onBackgroundClick={handleBackgroundClick}
        nodeLabel={(n: any) => {
          const data = n.data || {};
          const details = Object.entries(data)
            .filter(([k]) => k !== 'label' && k !== 'id' && k !== 'entity')
            .slice(0, 8)
            .map(([k, v]) => `<div style="font-size: 11px; margin-top: 2px;"><span style="color: #64748b; font-weight: 500;">${k}:</span> <span style="color: #1e293b;">${v}</span></div>`)
            .join("");
          
          return `
            <div style="background: white; padding: 12px; border-radius: 10px; border: 1px solid #e2e8f0; box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1); min-width: 180px;">
              <div style="font-weight: 700; color: #0f172a; font-size: 13px; margin-bottom: 6px; border-bottom: 1px solid #f1f5f9; padding-bottom: 4px;">
                ${n.label}
              </div>
              ${details || '<div style="font-size: 11px; color: #94a3b8;">No additional metadata</div>'}
              ${Object.keys(data).length > 8 ? '<div style="font-size: 10px; color: #94a3b8; margin-top: 6px; font-style: italic;">+ more details...</div>' : ''}
            </div>
          `;
        }}
        nodeColor={(n: any) => {
          if (selectedNode && n.id === selectedNode.id) return "#0f172a"; // Highlight selected node in sharp, high-contrast dark slate
          const isHighlight = highlightIds.includes(n.id);
          const base = entityColors[n.entity] || "#3b82f6";
          return isHighlight ? base : base + "99";
        }}
        nodeVal={(n: any) => n.val || 4}
        linkColor={(link: any) => {
          const s = typeof link.source === 'object' ? link.source.id : link.source;
          const t = typeof link.target === 'object' ? link.target.id : link.target;
          return highlightIds.includes(s) && highlightIds.includes(t) ? "#0ea5e9" : "#e2e8f0";
        }}
        linkWidth={(link: any) => {
          const s = typeof link.source === 'object' ? link.source.id : link.source;
          const t = typeof link.target === 'object' ? link.target.id : link.target;
          return highlightIds.includes(s) && highlightIds.includes(t) ? 3 : 1;
        }}
        backgroundColor="rgba(0,0,0,0)"
        cooldownTicks={100}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.3}
      />
      {selectedNode && (
        <div className="node-detail-card" style={{ maxHeight: '60vh', overflowY: 'auto', position: 'absolute' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
            <h4 style={{ margin: 0 }}>{selectedNode.entity}</h4>
            <button
              onClick={() => onSelectNode(null)}
              style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '16px', fontWeight: 'bold', color: '#64748b' }}
            >
              ×
            </button>
          </div>
          <dl>
            {Object.entries(selectedNode.data || {}).map(([k, v]) => (
              <div key={k}>
                <dt>{k}</dt>
                <dd>{v || "—"}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}
    </div>
  );
}
