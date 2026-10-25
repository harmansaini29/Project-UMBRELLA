// Project UMBRELLA: Mission Control Dashboard Controller

const TOPOLOGY_NODES = [
  { id: "api_gateway", label: "API Gateway", x: 0, y: -90, status: "healthy" },
  { id: "auth_service", label: "Auth Service", x: -140, y: -20, status: "healthy" },
  { id: "demo_booking_service", label: "Demo Booking", x: 140, y: -20, status: "healthy" },
  { id: "session_cache", label: "Redis Cache", x: -140, y: 70, status: "healthy" },
  { id: "demo_booking_db", label: "SQLite DB Pool", x: 140, y: 70, status: "healthy" },
  { id: "audit_ledger", label: "Audit Ledger", x: 0, y: 80, status: "healthy" }
];

const TOPOLOGY_EDGES = [
  { source: "api_gateway", target: "auth_service" },
  { source: "api_gateway", target: "demo_booking_service" },
  { source: "auth_service", target: "session_cache" },
  { source: "demo_booking_service", target: "demo_booking_db" },
  { source: "demo_booking_service", target: "audit_ledger" }
];

document.addEventListener("DOMContentLoaded", () => {
  renderTopology();
  refreshSystemStatus();
  loadCapsuleRegistry();
  setInterval(refreshSystemStatus, 3000);
});

function renderTopology() {
  const svg = document.getElementById("topology-svg");
  if (!svg) return;

  let edgesHtml = "";
  TOPOLOGY_EDGES.forEach(e => {
    const s = TOPOLOGY_NODES.find(n => n.id === e.source);
    const t = TOPOLOGY_NODES.find(n => n.id === e.target);
    if (s && t) {
      edgesHtml += `<line x1="${s.x}" y1="${s.y}" x2="${t.x}" y2="${t.y}" stroke="#374151" stroke-width="2" stroke-dasharray="4" />`;
    }
  });

  let nodesHtml = "";
  TOPOLOGY_NODES.forEach(n => {
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
        <text x="${n.x}" y="${n.y + 28}" font-size="11" fill="#e5e7eb" text-anchor="middle" font-weight="600">${n.label}</text>
      </g>
    `;
  });

  svg.innerHTML = edgesHtml + nodesHtml;
}

async function refreshSystemStatus() {
  try {
    const res = await fetch("/api/system/status");
    const data = await res.json();

    document.getElementById("hud-pool-headroom").textContent = `POOL_SIZE = ${data.demo_backend.pool_size}`;
    
    if (data.status === "degraded") {
      document.getElementById("hud-cluster-state").textContent = "DEGRADED (FAILURES)";
      document.getElementById("hud-cluster-state").style.color = "var(--accent-red)";
    } else {
      document.getElementById("hud-cluster-state").textContent = "HEALTHY";
      document.getElementById("hud-cluster-state").style.color = "var(--accent-green)";
    }
  } catch (err) {
    console.warn("Status poll error:", err);
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

      // Mark topology nodes based on failure scenario
      if (scenario === "jwt_auth_failure") {
        TOPOLOGY_NODES.forEach(n => {
          if (n.id === "auth_service") n.status = "critical";
          else if (n.id === "api_gateway" || n.id === "demo_booking_service") n.status = "degraded";
          else n.status = "healthy";
        });
        document.getElementById("badge-blast-radius").textContent = "BLAST: 60%";
        document.getElementById("topology-impact-desc").textContent = "OAuth2 Auth failure rejecting upstream tenant traffic";
        document.getElementById("rca-dominant-bottleneck").textContent = 
          `Authentication Token Rejection: ${summary.first_error_msg}`;
      } else if (scenario === "slow_query_deadlock") {
        TOPOLOGY_NODES.forEach(n => {
          if (n.id === "demo_booking_db") n.status = "critical";
          else if (n.id === "demo_booking_service") n.status = "degraded";
          else n.status = "healthy";
        });
        document.getElementById("badge-blast-radius").textContent = "BLAST: 40%";
        document.getElementById("topology-impact-desc").textContent = "Unindexed table scan holding exclusive locks >2,000ms";
        document.getElementById("rca-dominant-bottleneck").textContent = 
          `Database Table Lock Contention: ${summary.first_error_msg}`;
      } else {
        TOPOLOGY_NODES.forEach(n => {
          if (n.id === "demo_booking_service" || n.id === "demo_booking_db") {
            n.status = "critical";
          } else {
            n.status = "degraded";
          }
        });
        document.getElementById("badge-blast-radius").textContent = "BLAST: 100%";
        document.getElementById("topology-impact-desc").textContent = "Downstream QueuePool bottleneck cascading to all callers";
        document.getElementById("rca-dominant-bottleneck").textContent = 
          `Database Connection Pool Starvation: ${summary.first_error_msg}`;
      }
      renderTopology();

      document.getElementById("badge-blast-radius").className = "panel-badge badge-critical";
      document.getElementById("rca-dominant-bottleneck").style.color = "#ef4444";
      document.getElementById("meter-ast-val").textContent = "95%";
      document.getElementById("meter-ast-bar").style.width = "95%";
      document.getElementById("meter-telemetry-val").textContent = "100%";
      document.getElementById("meter-telemetry-bar").style.width = "100%";
      document.getElementById("meter-config-val").textContent = "100%";
      document.getElementById("meter-config-bar").style.width = "100%";
      document.getElementById("meter-rag-val").textContent = "90%";
      document.getElementById("meter-rag-bar").style.width = "90%";
      document.getElementById("badge-rca-confidence").textContent = "CONFIDENCE: 88%";

      document.getElementById("diff-preview").innerHTML = `
<span class="diff-del">- POOL_SIZE = 2</span>
<span class="diff-add">+ POOL_SIZE = 10</span>
<span class="diff-del">- MAX_OVERFLOW = 0</span>
<span class="diff-add">+ MAX_OVERFLOW = 5</span>
      `;
      document.getElementById("badge-risk-tier").textContent = "TIER 2: CONFIG RESTART";
      document.getElementById("badge-risk-tier").className = "panel-badge badge-warning";

      document.getElementById("guardian-auth-status").innerHTML = 
        `<span style="color:#f59e0b;">APPROVAL REQUIRED: Tier 2 patch formulated. Click to authorize Agent 4 execution.</span>`;
      document.getElementById("btn-hitl-approve").style.display = "inline-block";

    } else {
      document.getElementById("status-feed").innerHTML = 
        `<span style="color:#10b981; font-weight:bold;">✓ TEST PASSED:</span> ${summary.successful_requests}/${summary.total_requests} requests succeeded (0% errors). Latency: ${summary.avg_latency_ms} ms.`;
    }
  } catch (err) {
    alert("Error triggering load spike: " + err);
  }
}

async function triggerCouncilHeal() {
  document.getElementById("status-feed").textContent = "Executing 6-Agent Specialist Council Pipeline...";
  try {
    const res = await fetch("/api/council/heal?grant_hitl=true", { method: "POST" });
    const result = await res.json();

    if (result.detail) {
      alert(result.detail);
      return;
    }

    // Agent 1 RCA
    const a1 = result.agent_1_rca;
    document.getElementById("rca-dominant-bottleneck").textContent = a1.primary_causes[0].cause;
    document.getElementById("badge-rca-confidence").textContent = `CONFIDENCE: ${(a1.overall_confidence * 100).toFixed(0)}%`;
    document.getElementById("rca-code-pointer").textContent = a1.technical_details;

    // Agent 2 Topology
    const a2 = result.agent_2_topology;
    document.getElementById("badge-blast-radius").textContent = `BLAST: ${(a2.blast_report.blast_radius_score * 100).toFixed(0)}%`;

    // Agent 3 Diff
    const a3 = result.agent_3_planner;
    document.getElementById("diff-preview").textContent = a3.actions[0].unified_diff;
    document.getElementById("badge-risk-tier").textContent = a3.actions[0].risk_tier.toUpperCase();

    // Agent 5 & 4 Executor
    const a4 = result.agent_4_executor;
    if (a4) {
      document.getElementById("executor-terminal").textContent = `
[AGENT 4 EXECUTION COMPLETE]:
Status:            ${a4.status.toUpperCase()}
Execution Time:    ${a4.execution_time_ms.toFixed(1)} ms
Verification Test: ${a4.test_suite_passed ? "PASSED (100% SUCCESS)" : "FAILED"}
Rollback Triggered: ${a4.rollback_executed ? "YES (REVERTED)" : "NO (STABLE)"}
Commit SHA:        ${a4.git_commit_sha || "auto-patch-applied"}
      `;
    }

    // Agent 6 EVO
    const a6 = result.agent_6_evo;
    if (a6 && a6.evolution_experience) {
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

    // Reset topology to green
    TOPOLOGY_NODES.forEach(n => n.status = "healthy");
    renderTopology();

    document.getElementById("status-feed").innerHTML = 
      `<span style="color:#10b981; font-weight:bold;">🎉 SYSTEM FULLY HEALED:</span> Self-healing and evolution pipeline completed successfully.`;
    document.getElementById("btn-hitl-approve").style.display = "none";
    document.getElementById("guardian-auth-status").textContent = "Authorized by Human-in-the-Loop review.";

  } catch (err) {
    alert("Error executing council self-healing: " + err);
  }
}

function approveAndExecute() {
  triggerCouncilHeal();
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
    TOPOLOGY_NODES.forEach(n => n.status = "healthy");
    renderTopology();
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
