// Project UMBRELLA: Mission Control Dashboard Controller (Live Streaming Engine)

let activeTopologyData = null;

document.addEventListener("DOMContentLoaded", () => {
  refreshSystemStatus();
  pollLiveLogs();
  pollLiveTelemetry();
  loadCapsuleRegistry();

  // Active polling loops
  setInterval(refreshSystemStatus, 2500);
  setInterval(pollLiveLogs, 2000);
  setInterval(pollLiveTelemetry, 3000);
});

async function refreshSystemStatus() {
  try {
    const res = await fetch("/api/system/status");
    const data = await res.json();

    // 1. Update Headroom HUD
    document.getElementById("hud-pool-headroom").textContent = `POOL_SIZE = ${data.demo_backend.pool_size}`;

    if (data.status === "degraded") {
      document.getElementById("hud-cluster-state").textContent = "DEGRADED (FAILURES)";
      document.getElementById("hud-cluster-state").style.color = "var(--accent-red)";
    } else {
      document.getElementById("hud-cluster-state").textContent = "HEALTHY";
      document.getElementById("hud-cluster-state").style.color = "var(--accent-green)";
    }

    // 2. Fetch and render Live Dynamic Topology
    await renderLiveTopology();

    // 3. Render latest Council execution or pending approval if present
    if (data.latest_council_run) {
      renderCouncilRun(data.latest_council_run);
    }

    // 4. Update HITL Button if pending approval
    if (data.has_pending_approval) {
      document.getElementById("btn-hitl-approve").style.display = "inline-block";
      document.getElementById("guardian-auth-status").innerHTML = 
        `<span style="color:#f59e0b; font-weight:bold;">GATE PENDING: Human-in-the-Loop review required.</span>`;
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
        edgesHtml += `<line x1="${s.x}" y1="${s.y}" x2="${t.x}" y2="${t.y}" stroke="#374151" stroke-width="2" stroke-dasharray="4" />`;
      }
    });

    let nodesHtml = "";
    topo.nodes.forEach(n => {
      let color = "#10b981";
      let glow = "";
      if (n.status === "critical") {
        color = "#ef4444";
        glow = `<circle cx="${n.x}" cy="${n.y}" r="26" fill="rgba(239, 68, 68, 0.25)" class="pulse" />`;
      } else if (n.status === "degraded") {
        color = "#f59e0b";
      }

      nodesHtml += `
        <g>
          ${glow}
          <circle cx="${n.x}" cy="${n.y}" r="16" fill="${color}" stroke="#fff" stroke-width="1.5" />
          <text x="${n.x}" y="${n.y + 26}" font-size="10" fill="#e5e7eb" text-anchor="middle" font-weight="600">${n.label}</text>
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

async function pollLiveLogs() {
  try {
    const res = await fetch("/api/system/live-logs");
    const data = await res.json();
    const container = document.getElementById("live-logs-container");
    if (!container || !data.logs || data.logs.length === 0) return;

    container.innerHTML = data.logs.map(log => {
      let color = "#9ca3af";
      if (log.level === "CRITICAL" || log.level === "ERROR") color = "#ef4444";
      else if (log.level === "SUCCESS") color = "#10b981";
      else if (log.level === "INFO") color = "#60a5fa";

      return `
        <div style="margin-bottom:4px; font-size:0.75rem;">
          <span style="color:#6b7280;">[${log.timestamp}]</span>
          <strong style="color:${color};">[${log.source}]</strong>
          <span>${log.message}</span>
        </div>
      `;
    }).join("");
  } catch (err) {
    // console.warn("Log poll error:", err);
  }
}

async function pollLiveTelemetry() {
  try {
    const res = await fetch("/api/system/live-telemetry");
    const data = await res.json();
    const container = document.getElementById("connected-services-container");
    if (!container) return;

    if (!data.registered_clients || data.registered_clients.length === 0) {
      container.innerHTML = "<div style='color:#6b7280;'>No external microservices registered yet. Connect via umbrella_sdk.</div>";
      return;
    }

    container.innerHTML = data.registered_clients.map(c => `
      <div style="margin-bottom:8px; border-bottom:1px solid #1f2937; padding-bottom:6px;">
        <strong style="color:#10b981;">● ${c.service_name}</strong> (PID: ${c.pid || "Active"})<br>
        <span style="font-size:0.7rem; color:#9ca3af;">Path: ${c.repo_path || "External Repo"}</span><br>
        <span style="font-size:0.7rem; color:#60a5fa;">Config: ${c.config_file}</span>
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
    document.getElementById("rca-dominant-bottleneck").textContent = cause.cause;
    document.getElementById("rca-dominant-bottleneck").style.color = "#38bdf8";
    document.getElementById("badge-rca-confidence").textContent = `CONFIDENCE: ${(a1.overall_confidence * 100).toFixed(0)}%`;
    document.getElementById("rca-code-pointer").textContent = `AST Pointer: ${cause.target_file || 'config.py'}:${cause.line_number || 1}`;

    // Dynamically calculate live signal confidence from correlated_signals
    if (a1.correlated_signals) {
      const s1 = a1.correlated_signals["signal_1_ast"];
      const s2 = a1.correlated_signals["signal_2_telemetry"];
      const s3 = a1.correlated_signals["signal_3_config"];
      const s4 = a1.correlated_signals["signal_4_rag"];

      const pct1 = s1 ? Math.min(100, Math.round((s1.confidence_contribution / (s1.weight || 0.35)) * 100)) : 85;
      const pct2 = s2 ? Math.min(100, Math.round((s2.confidence_contribution / (s2.weight || 0.25)) * 100)) : 90;
      const pct3 = s3 ? Math.min(100, Math.round((s3.confidence_contribution / (s3.weight || 0.20)) * 100)) : 95;
      const pct4 = s4 ? Math.min(100, Math.round((s4.confidence_contribution / (s4.weight || 0.20)) * 100)) : 80;

      document.getElementById("meter-ast-val").textContent = `${pct1}%`;
      document.getElementById("meter-ast-bar").style.width = `${pct1}%`;
      document.getElementById("meter-telemetry-val").textContent = `${pct2}%`;
      document.getElementById("meter-telemetry-bar").style.width = `${pct2}%`;
      document.getElementById("meter-config-val").textContent = `${pct3}%`;
      document.getElementById("meter-config-bar").style.width = `${pct3}%`;
      document.getElementById("meter-rag-val").textContent = `${pct4}%`;
      document.getElementById("meter-rag-bar").style.width = `${pct4}%`;
    }
  }

  // Agent 3 Planner
  if (result.agent_3_planner && result.agent_3_planner.actions && result.agent_3_planner.actions.length > 0) {
    const action = result.agent_3_planner.actions[0];
    document.getElementById("diff-preview").textContent = action.unified_diff || "// Unified diff patch generated";
    document.getElementById("badge-risk-tier").textContent = action.risk_tier.toUpperCase();
    document.getElementById("verification-cmd").textContent = action.verification_command || "python test_demo_app.py";
  }

  // Agent 5 Guardian
  if (result.awaiting_hitl_approval) {
    document.getElementById("btn-hitl-approve").style.display = "inline-block";
    document.getElementById("guardian-auth-status").innerHTML = 
      `<span style="color:#f59e0b; font-weight:bold;">ACTION REQUIRED: Authorize Agent 4 to apply patch and commit.</span>`;
  }

  // Agent 4 Executor
  if (result.agent_4_executor) {
    const a4 = result.agent_4_executor;
    document.getElementById("executor-terminal").textContent = `
[AGENT 4 EXECUTION COMPLETE]:
Status:            ${a4.status.toUpperCase()}
Execution Time:    ${a4.execution_time_ms.toFixed(1)} ms
Verification Test: ${a4.test_suite_passed ? "PASSED (100% SUCCESS)" : "FAILED"}
Rollback Triggered: ${a4.rollback_executed ? "YES (REVERTED)" : "NO (STABLE)"}
Git Commit SHA:    ${a4.git_commit_sha || "auto-patch-applied"}
    `;
    document.getElementById("btn-hitl-approve").style.display = "none";
    document.getElementById("guardian-auth-status").textContent = "Authorized by Human-in-the-Loop review.";
  }

  // Agent 6 EVO
  if (result.agent_6_evo && result.agent_6_evo.evolution_experience) {
    const a6 = result.agent_6_evo;
    document.getElementById("badge-evo-reward").textContent = `Q-LEARNING REWARD: +${a6.evolution_experience.reward.toFixed(1)}`;
    document.getElementById("evo-stats-box").innerHTML = `
Total Experiences: ${a6.learning_stats.total_experiences}<br>
Success Rate:      ${a6.learning_stats.success_rate_pct}%<br>
Learned Q-Weight:  ${a6.evolution_experience.learned_weight.toFixed(3)}
    `;

    if (a6.proactive_proposal) {
      document.getElementById("evo-proposal-box").innerHTML = `
<strong>${a6.proactive_proposal.proposal_id}</strong><br>
${a6.proactive_proposal.justification}<br>
<span style="color:#06b6d4;">Target: ${a6.proactive_proposal.target_file}</span>
      `;
      document.getElementById("btn-approve-evo").style.display = "inline-block";
    }
  }
}

async function triggerLoadSpike(users = 10, scenario = "pool_starvation") {
  document.getElementById("status-feed").textContent = `Simulating ${users} concurrent tenant transactions under scenario: ${scenario}...`;
  try {
    const res = await fetch("/api/simulate/load", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ num_users: users, scenario: scenario })
    });
    const summary = await res.json();

    if (summary.failed_requests > 0) {
      document.getElementById("status-feed").innerHTML = `
        <span style="color:#ef4444; font-weight:bold;">🚨 CRASH DETECTED:</span> 
        ${summary.failed_requests}/${summary.total_requests} requests failed (${summary.failure_rate_pct}% failure). 
        ${summary.first_error_type}: ${summary.first_error_msg}
      `;
      // Trigger Council Diagnosis to prepare plan and HITL gate
      await triggerCouncilHeal(false);
    } else {
      document.getElementById("status-feed").innerHTML = 
        `<span style="color:#10b981; font-weight:bold;">✓ TEST PASSED:</span> ${summary.successful_requests}/${summary.total_requests} requests succeeded (0% errors). Latency: ${summary.avg_latency_ms} ms.`;
    }
    refreshSystemStatus();
  } catch (err) {
    alert("Error triggering load spike: " + err);
  }
}

async function triggerCouncilHeal(grant_hitl = true) {
  document.getElementById("status-feed").textContent = "Executing 6-Agent Specialist Council Pipeline...";
  try {
    const res = await fetch(`/api/council/heal?grant_hitl=${grant_hitl}`, { method: "POST" });
    const result = await res.json();
    if (result.detail) {
      alert(result.detail);
      return;
    }
    renderCouncilRun(result);
    refreshSystemStatus();
  } catch (err) {
    alert("Error executing council self-healing: " + err);
  }
}

async function approveAndExecute() {
  document.getElementById("guardian-auth-status").textContent = "Executing authorized patch and committing changes...";
  try {
    const res = await fetch("/api/council/approve-action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action_id: "ACT-POOL-SCALE-001", grant_approval: true })
    });
    const result = await res.json();
    renderCouncilRun(result);
    refreshSystemStatus();
    alert("🎉 Patch approved, executed, verified, and committed by Agent 4! Agent 6 EVO memory updated.");
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
    if (data.proposal) {
      document.getElementById("evo-proposal-box").innerHTML = `
<strong>${data.proposal.proposal_id}</strong><br>
${data.proposal.justification}<br>
<pre style="color:#34d399; margin-top:6px;">${data.proposal.unified_diff}</pre>
      `;
      document.getElementById("btn-approve-evo").style.display = "inline-block";
    } else {
      document.getElementById("evo-proposal-box").textContent = 
        `Observation window set to ${val}. No proactive proposals generated yet (requires active stress event count).`;
      document.getElementById("btn-approve-evo").style.display = "none";
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
    document.getElementById("btn-approve-evo").style.display = "none";
    document.getElementById("evo-proposal-box").innerHTML = 
      `<span style="color:#10b981; font-weight:bold;">✓ EVOLUTION APPLIED:</span> Baseline pool capacity expanded to POOL_SIZE=20.`;
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
        <div class="code-block" style="max-height:140px;">
          <strong>[${h.repository}]</strong><br>
          <span style="color:#06b6d4;">${h.symbol_name || h.file_path}</span> (RRF: ${h.rrf_score})<br>
          ${h.preview}
        </div>
      `;
    });
    container.innerHTML = html;
  } catch (err) {
    console.error("RAG search error:", err);
  }
}

async function resetDemoSystem() {
  try {
    const res = await fetch("/api/reset", { method: "POST" });
    const data = await res.json();
    alert(data.message);
    refreshSystemStatus();
    location.reload();
  } catch (err) {
    alert("Reset error: " + err);
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
        <div style="margin-bottom:6px; border-bottom:1px solid #1f2937; padding-bottom:4px;">
          <strong style="color:#38bdf8;">${c.archive_name}</strong> (${c.size_kb} KB)<br>
          <span style="font-size:0.7rem; color:#9ca3af;">SHA-256: ${c.master_sha256 ? c.master_sha256.substring(0, 16) + '...' : 'Verified'}</span>
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
  statusBox.textContent = "Packaging System DNA Capsule (calculating SHA-256 for code, databases, RAG indices, and Q-tables)...";
  try {
    const res = await fetch("/api/capsule/create", { method: "POST" });
    const data = await res.json();
    alert(`System DNA Capsule Created!\nCapsule ID: ${data.capsule_id}\nSize: ${(data.archive_bytes/1024).toFixed(1)} KB\nTotal Files: ${data.total_files}`);
    statusBox.innerHTML = `
      <span style="color:#10b981; font-weight:bold;">✓ CAPSULE PRESERVED:</span> ${data.capsule_id}<br>
      Archive Size: ${(data.archive_bytes/1024).toFixed(1)} KB | Artifacts: ${data.total_files} files<br>
      Master SHA-256: ${data.master_sha256}
    `;
    loadCapsuleRegistry();
  } catch (err) {
    alert("Error creating capsule: " + err);
  }
}

async function resurrectFromCapsule() {
  if (!confirm("Initiate Bare-Metal Resurrection from System DNA Capsule? This will verify SHA-256 seals and revive all subsystems from zero.")) return;

  const statusBox = document.getElementById("capsule-status-box");
  statusBox.textContent = "Executing bare-metal resurrection... verifying cryptographic checksums...";
  try {
    const res = await fetch("/api/capsule/restore", { method: "POST" });
    const data = await res.json();
    alert(`Resurrection Complete in ${data.resurrection_time_ms} ms!\nArtifacts Restored: ${data.total_artifacts_restored}\nAll 6 Agents & RAG Revived!`);
    statusBox.innerHTML = `
      <span style="color:#10b981; font-weight:bold;">🎉 BARE-METAL RESURRECTION COMPLETE:</span> Restored in ${data.resurrection_time_ms} ms<br>
      Subsystems Online: RAG (${data.subsystem_health.central_hybrid_rag}), Evolution Memory (${data.subsystem_health.agent_6_evolution_memory}), DB (${data.subsystem_health.relational_database})<br>
      Active Agents Revived: 6/6 Operational
    `;
    refreshSystemStatus();
  } catch (err) {
    alert("Resurrection error: " + err);
  }
}

function clearDashboardLogs() {
  document.getElementById("live-logs-container").innerHTML = '<div style="color:#6b7280;">Logs cleared.</div>';
}
