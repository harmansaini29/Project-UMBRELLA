"""
Agent 2: 3D Spatial Topology Visualizer
Models microservice mesh, computes blast radius, and generates 3D spatial representations.
"""

import math
from typing import Dict, List, Set, Optional, Tuple, Any
from agents.schemas import (
    TopologyNode,
    TopologyEdge,
    BlastRadiusReport,
    RCAResult,
    ImpactLevel
)


class TopologyVisualizer:
    """
    Agent 2 in the UMBRELLA Council.
    Maintains a 3D topological model of all software services and resources,
    computes failure propagation paths, and renders interactive spatial graphs.
    """

    def __init__(self):
        self.nodes: Dict[str, TopologyNode] = {}
        self.edges: List[TopologyEdge] = []
        self._adjacency_out: Dict[str, List[str]] = {}
        self._adjacency_in: Dict[str, List[str]] = {}
        self._build_default_cluster()

    def _build_default_cluster(self):
        """Initializes baseline enterprise topology."""
        default_nodes = [
            TopologyNode(id="api_gateway", name="API Gateway / Ingress", kind="service", position_3d={"x": 0.0, "y": 150.0, "z": 0.0}),
            TopologyNode(id="auth_service", name="OAuth2 Auth Service", kind="service", position_3d={"x": -120.0, "y": 50.0, "z": -40.0}),
            TopologyNode(id="payment_service", name="Payment Microservice", kind="service", position_3d={"x": 120.0, "y": 50.0, "z": -40.0}),
            TopologyNode(id="payment_db", name="Payment SQLite/Postgres DB", kind="database", position_3d={"x": 160.0, "y": -80.0, "z": 60.0}),
            TopologyNode(id="audit_ledger", name="Audit Ledger Queue", kind="queue", position_3d={"x": 60.0, "y": -80.0, "z": 120.0}),
            TopologyNode(id="session_cache", name="Redis Session Cache", kind="cache", position_3d={"x": -160.0, "y": -80.0, "z": 60.0}),
            TopologyNode(id="notification_worker", name="Notification Worker", kind="service", position_3d={"x": 0.0, "y": -120.0, "z": 0.0})
        ]

        default_edges = [
            TopologyEdge(source="api_gateway", target="auth_service", latency_ms=12.4, traffic_rps=120.0),
            TopologyEdge(source="api_gateway", target="payment_service", latency_ms=18.6, traffic_rps=85.0),
            TopologyEdge(source="auth_service", target="session_cache", latency_ms=2.1, traffic_rps=150.0),
            TopologyEdge(source="payment_service", target="payment_db", latency_ms=45.2, traffic_rps=75.0),
            TopologyEdge(source="payment_service", target="audit_ledger", latency_ms=6.8, traffic_rps=75.0),
            TopologyEdge(source="audit_ledger", target="notification_worker", latency_ms=15.0, traffic_rps=40.0)
        ]

        for n in default_nodes:
            self.nodes[n.id] = n
            self._adjacency_out[n.id] = []
            self._adjacency_in[n.id] = []

        for e in default_edges:
            self.edges.append(e)
            self._adjacency_out[e.source].append(e.target)
            self._adjacency_in[e.target].append(e.source)

    def register_node(self, node: TopologyNode):
        self.nodes[node.id] = node
        if node.id not in self._adjacency_out:
            self._adjacency_out[node.id] = []
        if node.id not in self._adjacency_in:
            self._adjacency_in[node.id] = []

    def register_edge(self, edge: TopologyEdge):
        self.edges.append(edge)
        self._adjacency_out[edge.source].append(edge.target)
        self._adjacency_in[edge.target].append(edge.source)

    def compute_blast_radius(self, root_node_id: str, incident_id: str) -> BlastRadiusReport:
        """
        Calculates failure propagation and affected nodes using BFS traversal.
        """
        # Match node name or id
        resolved_id = None
        for n_id in self.nodes:
            if n_id in root_node_id or root_node_id in n_id:
                resolved_id = n_id
                break

        if not resolved_id:
            resolved_id = root_node_id
            # Add synthetic node if missing
            self.register_node(TopologyNode(id=resolved_id, name=resolved_id, kind="service"))

        # Mark root node status
        self.nodes[resolved_id].status = "critical"

        # Downstream BFS (who depends on root_node_id? All parents in _adjacency_in)
        # Upstream BFS (who does root_node_id call? All children in _adjacency_out)
        impacted: Set[str] = set()

        # Traverse upstream (services that call this broken service)
        queue = [resolved_id]
        visited = {resolved_id}
        while queue:
            curr = queue.pop(0)
            # Callers are impacted because their dependency is down
            for caller in self._adjacency_in.get(curr, []):
                if caller not in visited:
                    visited.add(caller)
                    impacted.add(caller)
                    queue.append(caller)
                    if self.nodes[caller].status != "critical":
                        self.nodes[caller].status = "degraded"

            # Direct dependents of this resource
            for dep in self._adjacency_out.get(curr, []):
                if dep not in visited:
                    visited.add(dep)
                    impacted.add(dep)
                    queue.append(dep)
                    if self.nodes[dep].status != "critical":
                        self.nodes[dep].status = "degraded"

        total_nodes = max(len(self.nodes), 1)
        score = round((len(impacted) + 1) / total_nodes, 3)

        impact_desc = "Isolated single component"
        if score > 0.5:
            impact_desc = "Cluster-wide cascading degradation: Ingress & dependent payment transactions affected"
        elif score > 0.2:
            impact_desc = "Subsystem degradation: Direct upstream callers experiencing elevated error rates"

        return BlastRadiusReport(
            incident_id=incident_id,
            root_node_id=resolved_id,
            impacted_node_ids=sorted(list(impacted)),
            blast_radius_score=score,
            estimated_user_impact=impact_desc
        )

    def update_from_rca(self, rca: RCAResult) -> Tuple[BlastRadiusReport, Dict[str, Any]]:
        """
        Updates topology state from Agent 1 RCA diagnosis with dynamic semantic resolution.
        """
        root_component = "payment_service"
        sub_comp = ""
        if rca.primary_causes:
            full_comp = rca.primary_causes[0].source_component
            parts = full_comp.split(".")
            root_component = parts[0]
            if len(parts) > 1:
                sub_comp = parts[1]

        # Semantic mapping to topological graph
        if "auth" in sub_comp or "jwt" in sub_comp:
            target_node = "auth_service"
        elif "validator" in sub_comp or "ingress" in sub_comp:
            target_node = "api_gateway"
        elif "karamstay" in root_component or "demo" in root_component or "payment" in root_component:
            target_node = "payment_service"
        else:
            target_node = root_component

        blast_report = self.compute_blast_radius(target_node, rca.incident_id)

        topology_snapshot = {
            "incident_id": rca.incident_id,
            "root_node": blast_report.root_node_id,
            "blast_radius_score": blast_report.blast_radius_score,
            "impacted_nodes": blast_report.impacted_node_ids,
            "nodes": [
                {
                    "id": n.id,
                    "name": n.name,
                    "kind": n.kind,
                    "status": n.status,
                    "utilization_pct": n.utilization_pct,
                    "position": n.position_3d
                }
                for n in self.nodes.values()
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "latency_ms": e.latency_ms,
                    "traffic_rps": e.traffic_rps,
                    "healthy": e.healthy
                }
                for e in self.edges
            ]
        }

        return blast_report, topology_snapshot

    def generate_html_visualization(self, blast_report: BlastRadiusReport) -> str:
        """
        Generates interactive 3D WebGL / SVG canvas visualization for operator UI.
        """
        nodes_json = [
            f"""{{ id: "{n.id}", label: "{n.name}", kind: "{n.kind}", status: "{n.status}", x: {n.position_3d['x']}, y: {n.position_3d['y']}, z: {n.position_3d['z']} }}"""
            for n in self.nodes.values()
        ]
        edges_json = [
            f"""{{ source: "{e.source}", target: "{e.target}", latency: {e.latency_ms} }}"""
            for e in self.edges
        ]

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>UMBRELLA 3D Spatial Topology Visualizer</title>
  <style>
    body {{ margin: 0; background-color: #0b0f19; color: #f3f4f6; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; overflow: hidden; }}
    #hud {{ position: absolute; top: 16px; left: 16px; background: rgba(17, 24, 39, 0.85); padding: 16px; border-radius: 8px; border: 1px solid #374151; max-width: 380px; z-index: 100; backdrop-filter: blur(4px); }}
    .badge-critical {{ background: #ef4444; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; }}
    .badge-degraded {{ background: #f59e0b; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; }}
    .metric-row {{ display: flex; justify-content: space-between; margin: 6px 0; border-bottom: 1px solid #1f2937; padding-bottom: 4px; }}
    svg {{ width: 100vw; height: 100vh; }}
    .node-circle {{ transition: r 0.3s ease; cursor: pointer; }}
    .node-circle:hover {{ filter: drop-shadow(0 0 12px currentColor); }}
    .edge-line {{ stroke: #4b5563; stroke-width: 2; stroke-dasharray: 4; animation: dash 20s linear infinite; }}
    @keyframes dash {{ to {{ stroke-dashoffset: -1000; }} }}
  </style>
</head>
<body>
  <div id="hud">
    <h3 style="margin-top:0; color:#60a5fa;">Project UMBRELLA — Agent 2 Topology</h3>
    <div class="metric-row"><span>Root Incident:</span> <span class="badge-critical">{blast_report.root_node_id}</span></div>
    <div class="metric-row"><span>Blast Radius Score:</span> <strong>{blast_report.blast_radius_score * 100:.1f}%</strong></div>
    <div class="metric-row"><span>Impacted Nodes:</span> <span>{len(blast_report.impacted_node_ids)} downstream</span></div>
    <div class="metric-row"><span>Estimated Impact:</span> <span style="font-size:0.85em; text-align:right;">{blast_report.estimated_user_impact}</span></div>
  </div>

  <svg id="canvas" viewBox="-400 -300 800 600">
    <defs>
      <radialGradient id="grad-critical" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stop-color="#f87171"/>
        <stop offset="100%" stop-color="#b91c1c"/>
      </radialGradient>
      <radialGradient id="grad-degraded" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stop-color="#fbbf24"/>
        <stop offset="100%" stop-color="#b45309"/>
      </radialGradient>
      <radialGradient id="grad-healthy" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stop-color="#34d399"/>
        <stop offset="100%" stop-color="#047857"/>
      </radialGradient>
    </defs>
    <g id="edges-group"></g>
    <g id="nodes-group"></g>
  </svg>

  <script>
    const nodes = [{", ".join(nodes_json)}];
    const edges = [{", ".join(edges_json)}];

    const edgesGroup = document.getElementById("edges-group");
    edges.forEach(e => {{
      const src = nodes.find(n => n.id === e.source);
      const tgt = nodes.find(n => n.id === e.target);
      if (src && tgt) {{
        const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
        line.setAttribute("x1", src.x);
        line.setAttribute("y1", src.y);
        line.setAttribute("x2", tgt.x);
        line.setAttribute("y2", tgt.y);
        line.setAttribute("class", "edge-line");
        edgesGroup.appendChild(line);
      }}
    }});

    const nodesGroup = document.getElementById("nodes-group");
    nodes.forEach(n => {{
      const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
      g.setAttribute("transform", `translate(${{n.x}}, ${{n.y}})`);

      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("r", n.status === "critical" ? "28" : "20");
      circle.setAttribute("fill", n.status === "critical" ? "url(#grad-critical)" : (n.status === "degraded" ? "url(#grad-degraded)" : "url(#grad-healthy)"));
      circle.setAttribute("class", "node-circle");

      const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
      text.setAttribute("y", "36");
      text.setAttribute("text-anchor", "middle");
      text.setAttribute("fill", "#e5e7eb");
      text.setAttribute("font-size", "11px");
      text.textContent = n.label;

      g.appendChild(circle);
      g.appendChild(text);
      nodesGroup.appendChild(g);
    }});
  </script>
</body>
</html>"""
        return html
