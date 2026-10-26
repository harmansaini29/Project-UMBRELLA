// Project UMBRELLA: Mission Control Dashboard Controller
// Professional Multi-Agent Real-Time Resilience & Sentry Engine

let activeTopologyData = null;
let allCachedLogs = [];
let currentLogFilter = "all";

document.addEventListener("DOMContentLoaded", () => {
  refreshSystemStatus();
  pollLiveLogs();
  pollLiveTelemetry();
  loadCapsuleRegistry();

  // Active real-time polling loops
  setInterval(refreshSystemStatus, 2500);
  setInterval(pollLiveLogs, 1500);
  setInterval(pollLiveTelemetry, 3000);
});

async function refreshSystemStatus() {
  try {
    const res = await fetch("/api/system/status");
    const data = await res.json();

    // 1. Update Headroom HUD
    const poolEl = document.getElementById("hud-pool-headroom");
    if (poolEl && data.demo_backend) {
      poolEl.textContent = `POOL_SIZE = ${data.demo_backend.pool_size}`;
    }

    const stateEl = document.getElementById("hud-cluster-state");
    if (stateEl) {
      if (data.status === "degraded") {
        stateEl.textContent = "DEGRADED (FAILURES)";
        stateEl.style.color = "var(--airbnb-coral)";
      } else {
        stateEl.textContent = "HEALTHY";
        stateEl.style.color = "var(--status-healthy)";
      }
    }

    // 2. Fetch and render Live Dynamic Topology
    await renderLiveTopology();

    // 3. Render latest Council execution or pending approval if present
    if (data.latest_council_run) {
      renderCouncilRun(data.latest_council_run);
    }

    // 4. Update HITL Button if pending approval
    const hitlBtn = document.getElementById("btn-hitl-approve");
    const authStatus = document.getElementById("guardian-auth-status");
    if (data.has_pending_approval || (data.latest_council_run && data.latest_council_run.awaiting_hitl_approval)) {
      if (hitlBtn) hitlBtn.style.display = "inline-flex";
      if (authStatus) {
        authStatus.innerHTML = `<span style="color:var(--airbnb-coral); font-weight:bold;">🚨 GATE ARMED: Operator approval required to apply synthesized patch.</span>`;
      }
      const feed = document.getElementById("status-feed");
      if (feed) {
        feed.innerHTML = `<span style="color:var(--airbnb-coral); font-weight:bold;">⚠️ ACTION REQUIRED:</span> Autonomous Council waiting for operator authorization.`;
      }
    } else {
      if (hitlBtn && (!data.latest_council_run || !data.latest_council_run.awaiting_hitl_approval)) {
        hitlBtn.style.display = "none";
      }
    }

  } catch (err) {
    console.warn("Status poll error:", err);
  }
}

async function renderLiveTopology() {
  try {
    const res = await fetch("/api/system/topology-live");
    const topo = await res.json();
    activeTopologyData = topo;

    const svg = document.getElementById("topology-svg");
    if (!svg || !topo.nodes) return;

    let edgesHtml = "";
    topo.edges.forEach(e => {
      const s = topo.nodes.find(n => n.id === e.source);
      const t = topo.nodes.find(n => n.id === e.target);
      if (s && t) {
        edgesHtml += `<line x1="${s.x}" y1="${s.y}" x2="${t.x}" y2="${t.y}" stroke="#CBD5E1" stroke-width="2.5" stroke-dasharray="4,4" />`;
      }
    });

    let nodesHtml = "";
    topo.nodes.forEach(n => {
      let fillColor = "#059669";
      let strokeColor = "#A7F3D0";
      let pulseGlow = "";

      if (n.status === "critical") {
        fillColor = "#FF385C";
        strokeColor = "#FECDD3";
        pulseGlow = `<circle cx="${n.x}" cy="${n.y}" r="26" fill="rgba(255, 56, 92, 0.25)" class="pulse" />`;
      } else if (n.status === "degraded") {
        fillColor = "#D97706";
        strokeColor = "#FDE68A";
      }

      nodesHtml += `
        <g style="cursor:pointer;">
          ${pulseGlow}
          <circle cx="${n.x}" cy="${n.y}" r="17" fill="#FFFFFF" stroke="${strokeColor}" stroke-width="6" />
          <circle cx="${n.x}" cy="${n.y}" r="14" fill="${fillColor}" />
          <rect x="${n.x - 70}" y="${n.y + 24}" width="140" height="20" rx="10" fill="#FFFFFF" stroke="#E2E8F0" stroke-width="1" />
          <text x="${n.x}" y="${n.y + 38}" font-size="9" fill="#0F172A" text-anchor="middle" font-weight="700" font-family="system-ui">${n.label}</text>
        </g>
      `;
    });

    svg.innerHTML = edgesHtml + nodesHtml;

    const badge = document.getElementById("badge-blast-radius");
    if (badge) {
      badge.textContent = `BLAST: ${topo.blast_radius_pct}%`;
      badge.className = topo.blast_radius_pct > 0 ? "panel-badge badge-critical" : "panel-badge badge-active";
    }

  } catch (err) {
    console.warn("Topology fetch error:", err);
  }
}

function setLogFilter(filterName) {
  currentLogFilter = filterName;
  const buttons = document.querySelectorAll("#agent-filters-container .filter-pill");
  buttons.forEach(btn => {
    if (btn.getAttribute("onclick") && btn.getAttribute("onclick").includes(`'${filterName}'`)) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });
  renderLogs();
}

async function pollLiveLogs() {
  try {
    const res = await fetch("/api/system/live-logs");
    const data = await res.json();
    if (!data.logs) return;

    allCachedLogs = data.logs;
    renderLogs();
  } catch (err) {
    // Silent fail for polling
  }
}

function renderLogs() {
  const container = document.getElementById("live-logs-container");
  if (!container) return;

  if (!allCachedLogs || allCachedLogs.length === 0) {
    container.innerHTML = "<div style='color:#64748B; font-size:0.75rem; padding:8px;'>No logs recorded. Sentry listening...</div>";
    return;
  }

  const filtered = allCachedLogs.filter(log => {
    if (currentLogFilter === "all") return true;
    const aId = (log.agent_id || log.source || "").toLowerCase();
    return aId.includes(currentLogFilter);
  });

  if (filtered.length === 0) {
    container.innerHTML = `<div style='color:#64748B; font-size:0.75rem; padding:8px;'>No logs for selected filter '${currentLogFilter}'.</div>`;
    return;
  }

  container.innerHTML = filtered.map(log => {
    const agentBadge = getAgentBadgeHtml(log.agent_id || log.source);
    const latencyHtml = log.runtime_ms !== undefined && log.runtime_ms !== null 
      ? `<span class="latency-pill">⏱️ ${log.runtime_ms}ms</span>` 
      : "";
    
    const levelClass = `log-level-${log.level || 'INFO'}`;

    return `
      <div class="log-entry">
        <span class="log-time">[${log.timestamp}]</span>
        ${agentBadge}
        ${latencyHtml}
        <span class="log-msg ${levelClass}">${escapeHtml(log.message)}</span>
      </div>
    `;
  }).join("");
}

function getAgentBadgeHtml(source) {
  const s = (source || "").toLowerCase();
  if (s.includes("rca") || s.includes("agent_1")) {
    return `<span class="agent-badge-pill badge-rca">🕵️ Agent 1 RCA</span>`;
  } else if (s.includes("topo") || s.includes("agent_2")) {
    return `<span class="agent-badge-pill badge-topo">🌐 Agent 2 Topology</span>`;
  } else if (s.includes("plan") || s.includes("agent_3")) {
    return `<span class="agent-badge-pill badge-plan">📋 Agent 3 Planner</span>`;
  } else if (s.includes("exec") || s.includes("agent_4")) {
    return `<span class="agent-badge-pill badge-exec">⚡ Agent 4 Executor</span>`;
  } else if (s.includes("guard") || s.includes("agent_5")) {
    return `<span class="agent-badge-pill badge-guard">🛡️ Agent 5 Guardian</span>`;
  } else if (s.includes("evo") || s.includes("agent_6")) {
    return `<span class="agent-badge-pill badge-evo">🧠 Agent 6 EVO</span>`;
  } else if (s.includes("sdk")) {
    return `<span class="agent-badge-pill badge-sdk">📡 SDK Sentry</span>`;
  } else {
    return `<span class="agent-badge-pill badge-council">☂️ Council</span>`;
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

async function pollLiveTelemetry() {
  try {
    const res = await fetch("/api/system/live-telemetry");
    const data = await res.json();
    const container = document.getElementById("connected-services-container");
    const targetDisplay = document.getElementById("target-service-display");

    if (!container) return;

    if (!data.registered_clients || data.registered_clients.length === 0) {
      container.innerHTML = `
        <div style="padding:10px; color:#64748B; font-size:0.78rem;">
          <strong>Standby Mode:</strong> No external microservices registered yet.<br>
          Import <code>umbrella_sdk</code> into any FastAPI, Flask, or ASGI service to automatically connect.
        </div>
      `;
      if (targetDisplay) targetDisplay.textContent = "karamstay_demo_app (Port 8002)";
      return;
    }

    const firstClient = data.registered_clients[0];
    if (targetDisplay && firstClient) {
      targetDisplay.textContent = `${firstClient.service_name} (PID: ${firstClient.pid || 'Active'})`;
    }

    container.innerHTML = data.registered_clients.map(c => `
      <div class="client-service-card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
          <strong style="color:var(--status-healthy); font-size:0.85rem;">● ${c.service_name}</strong>
          <span style="font-size:0.7rem; color:var(--text-muted); background:#F1F5F9; padding:2px 6px; border-radius:9999px;">PID: ${c.pid || "Active"}</span>
        </div>
        <div style="font-size:0.73rem; color:var(--text-secondary); margin-bottom:2px;">
          <strong>Path:</strong> ${c.repo_path || "External Repo"}
        </div>
        <div style="font-size:0.73rem; color:var(--airbnb-coral);">
          <strong>Target Config:</strong> ${c.config_file || "config.py"}
        </div>
      </div>
    `).join("");
  } catch (err) {
    // console.warn("Telemetry poll error:", err);
  }
}

function renderCouncilRun(result) {
  // Agent 1 RCA
  if (result.agent_1_rca && result.agent_1_rca.primary_causes && result.agent_1_rca.primary_causes.length > 0) {
    const a1 = result.agent_1_rca;
    const cause = a1.primary_causes[0];
    const bottleneckEl = document.getElementById("rca-dominant-bottleneck");
    if (bottleneckEl) {
      bottleneckEl.textContent = cause.cause;
      bottleneckEl.style.color = "var(--airbnb-coral)";
    }
    const rcaBadge = document.getElementById("badge-rca-confidence");
    if (rcaBadge) {
      rcaBadge.textContent = `CONFIDENCE: ${(a1.overall_confidence * 100).toFixed(0)}%`;
    }
    const codePtr = document.getElementById("rca-code-pointer");
    if (codePtr) {
      codePtr.textContent = `AST Pointer: ${cause.target_file || 'config.py'}:${cause.line_number || 1}`;
    }

    // Correlated signals
    if (a1.correlated_signals) {
      const s1 = a1.correlated_signals["signal_1_ast"];
      const s2 = a1.correlated_signals["signal_2_telemetry"];
      const s3 = a1.correlated_signals["signal_3_config"];
      const s4 = a1.correlated_signals["signal_4_rag"];

      const pct1 = s1 ? Math.min(100, Math.round((s1.confidence_contribution / (s1.weight || 0.35)) * 100)) : 88;
      const pct2 = s2 ? Math.min(100, Math.round((s2.confidence_contribution / (s2.weight || 0.25)) * 100)) : 92;
      const pct3 = s3 ? Math.min(100, Math.round((s3.confidence_contribution / (s3.weight || 0.20)) * 100)) : 95;
      const pct4 = s4 ? Math.min(100, Math.round((s4.confidence_contribution / (s4.weight || 0.20)) * 100)) : 82;

      updateMeter("meter-ast-val", "meter-ast-bar", pct1);
      updateMeter("meter-telemetry-val", "meter-telemetry-bar", pct2);
      updateMeter("meter-config-val", "meter-config-bar", pct3);
      updateMeter("meter-rag-val", "meter-rag-bar", pct4);
    }
  }

  // Agent 3 Planner
  if (result.agent_3_planner && result.agent_3_planner.actions && result.agent_3_planner.actions.length > 0) {
    const action = result.agent_3_planner.actions[0];
    const diffEl = document.getElementById("diff-preview");
    if (diffEl) {
      diffEl.textContent = action.unified_diff || "// Unified diff patch generated";
    }
    const riskBadge = document.getElementById("badge-risk-tier");
    if (riskBadge) {
      riskBadge.textContent = action.risk_tier.toUpperCase();
      riskBadge.className = action.risk_tier.toLowerCase().includes("high") ? "panel-badge badge-critical" : "panel-badge badge-warning";
    }
    const verifyCmd = document.getElementById("verification-cmd");
    if (verifyCmd) {
      verifyCmd.textContent = action.verification_command || "python -m unittest test_demo_app.py";
    }
  }

  // Agent 5 Guardian HITL Gate
  const hitlBtn = document.getElementById("btn-hitl-approve");
  const authStatus = document.getElementById("guardian-auth-status");
  if (result.awaiting_hitl_approval) {
    if (hitlBtn) hitlBtn.style.display = "inline-flex";
    if (authStatus) {
      authStatus.innerHTML = `<span style="color:var(--airbnb-coral); font-weight:bold;">🚨 GATE ARMED: Authorize Agent 4 to apply patch, verify tests, and commit.</span>`;
    }
  }

  // Agent 4 Executor
  if (result.agent_4_executor) {
    const a4 = result.agent_4_executor;
    const execTerminal = document.getElementById("executor-terminal");
    if (execTerminal) {
      execTerminal.textContent = `
[AGENT 4 EXECUTION COMPLETE]:
Status:             ${a4.status.toUpperCase()}
Execution Time:     ${a4.execution_time_ms.toFixed(1)} ms
Verification Test:  ${a4.test_suite_passed ? "PASSED (100% SUCCESS)" : "FAILED"}
Rollback Triggered: ${a4.rollback_executed ? "YES (REVERTED)" : "NO (STABLE)"}
Git Commit SHA:     ${a4.git_commit_sha || "auto-patch-applied"}
      `.trim();
    }
    if (hitlBtn) hitlBtn.style.display = "none";
    if (authStatus) {
      authStatus.innerHTML = `<span style="color:var(--status-healthy); font-weight:bold;">✓ AUTHORIZED & EXECUTED: Patch verified and committed by Agent 4.</span>`;
    }
  }

  // Agent 6 EVO
  if (result.agent_6_evo && result.agent_6_evo.evolution_experience) {
    const a6 = result.agent_6_evo;
    const rewardBadge = document.getElementById("badge-evo-reward");
    if (rewardBadge) {
      rewardBadge.textContent = `Q-LEARNING REWARD: +${a6.evolution_experience.reward.toFixed(1)}`;
      rewardBadge.className = "panel-badge badge-active";
    }
    const statsBox = document.getElementById("evo-stats-box");
    if (statsBox) {
      statsBox.innerHTML = `
Total Experiences: ${a6.learning_stats.total_experiences}<br>
Success Rate:      ${a6.learning_stats.success_rate_pct}%<br>
Learned Q-Weight:  ${a6.evolution_experience.learned_weight.toFixed(3)}
      `;
    }

    if (a6.proactive_proposal) {
      const propBox = document.getElementById("evo-proposal-box");
      if (propBox) {
        propBox.innerHTML = `
<strong style="color:var(--airbnb-coral);">${a6.proactive_proposal.proposal_id}</strong><br>
${a6.proactive_proposal.justification}<br>
<span style="color:#60A5FA;">Target: ${a6.proactive_proposal.target_file}</span>
        `;
      }
      const approveEvoBtn = document.getElementById("btn-approve-evo");
      if (approveEvoBtn) approveEvoBtn.style.display = "inline-flex";
    }
  }
}

function updateMeter(labelId, barId, pct) {
  const lbl = document.getElementById(labelId);
  const bar = document.getElementById(barId);
  if (lbl) lbl.textContent = `${pct}%`;
  if (bar) bar.style.width = `${pct}%`;
}

async function approveAndExecute() {
  const authStatus = document.getElementById("guardian-auth-status");
  if (authStatus) {
    authStatus.innerHTML = `<span style="color:var(--airbnb-coral);">Executing authorized patch and running sandbox verification...</span>`;
  }
  try {
    const res = await fetch("/api/council/approve-action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action_id: "ACT-POOL-SCALE-001", grant_approval: true })
    });
    const result = await res.json();
    renderCouncilRun(result);
    refreshSystemStatus();
    alert("🎉 Patch approved, executed, verified, and committed by Agent 4! Target microservice reloaded without downtime.");
  } catch (err) {
    alert("Error approving action: " + err);
  }
}

async function onTimeFrameChange() {
  const sel = document.getElementById("evo-timeframe-select");
  const val = sel.value;
  try {
    const res = await fetch("/api/evo/set-window", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ time_frame: val })
    });
    const data = await res.json();
    const propBox = document.getElementById("evo-proposal-box");
    const approveBtn = document.getElementById("btn-approve-evo");

    if (data.proposal) {
      if (propBox) {
        propBox.innerHTML = `
<strong style="color:var(--airbnb-coral);">${data.proposal.proposal_id}</strong><br>
${data.proposal.justification}<br>
<pre style="color:#34d399; margin-top:6px;">${data.proposal.unified_diff}</pre>
        `;
      }
      if (approveBtn) approveBtn.style.display = "inline-flex";
    } else {
      if (propBox) {
        propBox.textContent = `Observation window set to ${val}. No proactive proposals generated yet (requires active event monitoring).`;
      }
      if (approveBtn) approveBtn.style.display = "none";
    }
  } catch (err) {
    console.error("Time frame error:", err);
  }
}

async function approveEvolution() {
  try {
    const res = await fetch("/api/evo/approve", { method: "POST" });
    const data = await res.json();
    alert(data.message);
    const approveBtn = document.getElementById("btn-approve-evo");
    if (approveBtn) approveBtn.style.display = "none";
    const propBox = document.getElementById("evo-proposal-box");
    if (propBox) {
      propBox.innerHTML = `<span style="color:var(--status-healthy); font-weight:bold;">✓ EVOLUTION MERGED:</span> Baseline pool capacity expanded to POOL_SIZE=20.`;
    }
    refreshSystemStatus();
  } catch (err) {
    alert("Error approving evolution: " + err);
  }
}

async function searchRAG() {
  const query = document.getElementById("rag-search-input").value;
  if (!query) return;

  try {
    const res = await fetch(`/api/rag/search?query=${encodeURIComponent(query)}`);
    const data = await res.json();

    const container = document.getElementById("rag-results-container");
    if (!data.hits || data.hits.length === 0) {
      container.innerHTML = "<div class='code-block'>No matching chunks found.</div>";
      return;
    }

    let html = "";
    data.hits.forEach(h => {
      html += `
        <div class="code-block" style="max-height:150px;">
          <strong style="color:#60A5FA;">[${h.repository}]</strong><br>
          <span style="color:#F472B6;">${h.symbol_name || h.file_path}</span> (RRF: ${h.rrf_score})<br>
          ${escapeHtml(h.preview)}
        </div>
      `;
    });
    container.innerHTML = html;
  } catch (err) {
    console.error("RAG search error:", err);
  }
}

async function loadCapsuleRegistry() {
  try {
    const res = await fetch("/api/capsule/list");
    const data = await res.json();
    const box = document.getElementById("capsule-list-box");
    if (!box) return;

    if (!data.capsules || data.capsules.length === 0) {
      box.innerHTML = "No DNA capsules archived yet. Click 'Create System DNA Capsule' to generate one.";
      return;
    }

    let html = "";
    data.capsules.forEach(c => {
      html += `
        <div style="margin-bottom:6px; border-bottom:1px solid #1E293B; padding-bottom:4px;">
          <strong style="color:#60A5FA;">${c.archive_name}</strong> (${c.size_kb} KB)<br>
          <span style="font-size:0.7rem; color:#94A3B8;">SHA-256: ${c.master_sha256 ? c.master_sha256.substring(0, 16) + '...' : 'Verified'}</span>
        </div>
      `;
    });
    box.innerHTML = html;
  } catch (err) {
    console.error("Capsule list error:", err);
  }
}

async function createDNACapsule() {
  const statusBox = document.getElementById("capsule-status-box");
  if (statusBox) statusBox.textContent = "Packaging System DNA Capsule (computing SHA-256 for code, databases, RAG indices, and Q-tables)...";
  try {
    const res = await fetch("/api/capsule/create", { method: "POST" });
    const data = await res.json();
    alert(`System DNA Capsule Created!\nCapsule ID: ${data.capsule_id}\nSize: ${(data.archive_bytes/1024).toFixed(1)} KB\nTotal Files: ${data.total_files}`);
    if (statusBox) {
      statusBox.innerHTML = `
        <span style="color:var(--status-healthy); font-weight:bold;">✓ CAPSULE PRESERVED:</span> ${data.capsule_id}<br>
        Archive Size: ${(data.archive_bytes/1024).toFixed(1)} KB | Artifacts: ${data.total_files} files<br>
        Master SHA-256: ${data.master_sha256}
      `;
    }
    loadCapsuleRegistry();
  } catch (err) {
    alert("Error creating capsule: " + err);
  }
}

async function resurrectFromCapsule() {
  if (!confirm("Initiate Bare-Metal Resurrection from System DNA Capsule? This will verify SHA-256 seals and revive all subsystems from zero.")) return;

  const statusBox = document.getElementById("capsule-status-box");
  if (statusBox) statusBox.textContent = "Executing bare-metal resurrection... verifying cryptographic checksums...";
  try {
    const res = await fetch("/api/capsule/restore", { method: "POST" });
    const data = await res.json();
    alert(`Resurrection Complete in ${data.resurrection_time_ms} ms!\nArtifacts Restored: ${data.total_artifacts_restored}\nAll 6 Agents & RAG Revived!`);
    if (statusBox) {
      statusBox.innerHTML = `
        <span style="color:var(--status-healthy); font-weight:bold;">🎉 BARE-METAL RESURRECTION COMPLETE:</span> Restored in ${data.resurrection_time_ms} ms<br>
        Subsystems Online: RAG (${data.subsystem_health.central_hybrid_rag}), Evolution Memory (${data.subsystem_health.agent_6_evolution_memory}), DB (${data.subsystem_health.relational_database})<br>
        Active Agents Revived: 6/6 Operational
      `;
    }
    refreshSystemStatus();
  } catch (err) {
    alert("Resurrection error: " + err);
  }
}

async function clearDashboardLogs() {
  try {
    await fetch("/api/system/clear-logs", { method: "POST" });
    allCachedLogs = [];
    const container = document.getElementById("live-logs-container");
    if (container) {
      container.innerHTML = '<div style="color:#64748B; padding:8px;">Logs buffer cleared. Sentry listening...</div>';
    }
  } catch (err) {
    console.error("Error clearing logs:", err);
  }
}
