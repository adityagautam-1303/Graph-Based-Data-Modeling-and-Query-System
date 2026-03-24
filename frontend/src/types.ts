export interface NodeData {
  id: string;
  label: string;
  entity: string;
  data: Record<string, string>;
}

export interface EdgeData {
  source: string;
  target: string;
  relation?: string;
}

export interface GraphData {
  nodes: NodeData[];
  edges: EdgeData[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sql?: string;
  data?: unknown[];
}
