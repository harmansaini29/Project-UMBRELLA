# Project UMBRELLA: Official Research Paper & Project Charter

**Title**: UMBRELLA: A Risk-Aware Multi-Agent Framework for Autonomous Backend Self-Healing, Behavioral Evolution, and Long-Term Recovery  
**Author**: Harman Saini  
**Affiliation**: Department of Computer Science and Engineering (Artificial Intelligence and Machine Learning), Chhatrapati Shivaji Maharaj University, India  
**Date**: October 2026  
**Document Status**: Official Research Charter & Architecture Foundation

---

## Abstract
Distributed backend systems combine APIs, databases, caches, asynchronous services, external dependencies, and rapidly changing configuration. Conventional monitoring and static recovery rules can identify and respond to known failures, but they do not inherently form an auditable feedback loop in which remediation outcomes improve later decisions. This paper proposes UMBRELLA, a risk-aware multi-agent framework for autonomous backend self-healing. Its primary research component, MVP1, is the Backend Evolution Agent, which maintains structured incident knowledge linking observed conditions, probable causes, candidate actions, execution outcomes, and post-recovery behavior. The agent uses this knowledge to adapt future remediation preferences inside a bounded action space controlled by confidence, risk, authorization, rollback, and audit constraints. The paper defines a reproducible multi-service testbed and an experimental methodology comparing static remediation with evolution-enabled remediation across recurring API, database, dependency, resource, latency, configuration, and cascading failures. Evaluation measures include mean time to detect (MTTD), mean time to recover (MTTR), diagnosis accuracy, remediation success, recurrence, human intervention, unsafe actions, adaptation gain, and control-plane overhead. MVP2 extends UMBRELLA with a Critical Survival Capsule Architecture. It introduces a Recovery Genome containing the minimum self-describing information needed to reconstruct a critical software ecosystem and proposes compression, encryption, error correction, erasure-coded sharding, integrity verification, and geographically independent archival. DNA is considered as a candidate long-duration physical storage medium, but physical DNA synthesis, preservation, sequencing, and post-disaster reconstruction are explicitly treated as future experimental work rather than claimed capabilities. The paper therefore separates the testable MVP1 contribution from the longer-term archival research direction.

**Keywords** — autonomous remediation, backend resilience, self-healing systems, self-adaptive systems, AIOps, AgentOps, root cause analysis, behavioral evolution, fault tolerance, long-term archival, DNA data storage.

---

## I. Introduction
Modern backend ecosystems are increasingly distributed across application services, databases, caches, queues, external APIs, container platforms, and cloud infrastructure. A failure in one component can produce secondary effects through dependency relationships, leading to degraded latency, resource exhaustion, unavailable services, inconsistent state, or cascading incidents. The operational challenge is therefore not only to detect a fault, but to identify its likely cause, select a safe intervention, determine whether the intervention worked, and use the outcome to improve future responses.

Autonomic computing established the broader goal of systems that manage themselves according to administrator-defined objectives [1]. Self-adaptive software subsequently developed feedback-oriented approaches in which systems observe their environment and change their behavior or configuration in response to changing conditions [2]. Autonomous self-healing research has also considered learning behavioral models from runtime observations because manually maintaining complete specifications becomes difficult as software evolves [3]. More recent AIOps and AgentOps research has emphasized end-to-end evaluation of agents across fault localization, root-cause analysis, and mitigation rather than evaluating isolated detection tasks [4], [5].

UMBRELLA builds on these foundations but narrows the research contribution to an experimentally testable question: **whether explicit, auditable learning from remediation outcomes can improve future autonomous backend recovery for recurring incidents**. The system is organized as a closed loop: 
$$\text{Observe} \rightarrow \text{Diagnose} \rightarrow \text{Assess} \rightarrow \text{Act} \rightarrow \text{Evaluate} \rightarrow \text{Learn} \rightarrow \text{Adapt}$$

The Backend Evolution Agent is responsible for converting incident history and observed outcomes into bounded behavioral adaptation; it is not defined as a conversational model that merely claims to learn.

The project is divided into two development stages:
- **MVP1**: The operational self-healing and behavioral-evolution system and the primary empirical contribution.
- **MVP2**: A catastrophic survival capsule extension based on a Recovery Genome and distributed survival capsules (including potential DNA storage).

---

## II. Related Work and Research Gap

### A. Self-Healing and Self-Adaptive Systems
Self-healing software detects failures and recovers with limited human intervention [1]. Self-adaptive software research studies architectures and feedback loops (MAPE-K) for runtime adaptation [2].

### B. AIOps and Autonomous Incident Management
AIOps combines logs, metrics, traces, and incidents for automated analysis [6]. AgentOps benchmarks (e.g., AIOpsLab [5]) evaluate agents operating on microservice systems.

### C. Runtime Behavioral Learning
Adaptive-immunity research argues runtime behavior can learn models for self-healing [3]. UMBRELLA records operational relationships between incident context, remediation choice, observed outcome, and subsequent behavior.

### D. DNA-Based Long-Term Data Storage
DNA provides high density and durability [7]–[10]. MVP2 treats DNA as a future physical storage layer rather than assuming petabyte-scale arbitrary storage today.

### E. Research Gap & Positioning
| Research Area | Established Direction | UMBRELLA Research Focus |
|---|---|---|
| Autonomic computing | Self-managing software [1] | Backend resilience control plane |
| Self-adaptation | MAPE-K loops [2], [4] | Multi-agent feedback with explicit outcome learning |
| Self-healing | Runtime detection & recovery [3] | Recurring-incident learning under safety limits |
| AIOps / AgentOps | Incident analysis/automation [5] | Closed-loop backend remediation evaluation |
| DNA archival | Dense, durable cold storage [7]–[10] | Future physical layer for Recovery Genome |

---

## III. Research Questions & Hypotheses

### Research Questions
- **RQ1**: Can outcome-driven behavioral evolution improve autonomous recovery decisions for recurring backend incidents compared with static remediation under the same action space?
- **RQ2**: Can risk-aware constraints reduce unsafe or unnecessary autonomous actions without preventing successful low-risk remediation?
- **RQ3**: Can a compact Recovery Genome provide a software-level abstraction for long-term reconstruction independent of the original production infrastructure?

### Research Hypotheses
- **H0**: There is no statistically meaningful difference between static and evolution-enabled remediation for the selected recovery metrics.
- **H1**: Evolution-enabled remediation improves one or more predefined recovery outcomes for recurring incident classes compared with static remediation.
- **H2**: Risk-aware constraints reduce unsafe or unnecessary actions relative to an otherwise equivalent unconstrained policy.
- **H3**: Recovery Genome packaging can reduce the amount of information requiring long-term preservation by selecting and representing only reconstruction-critical system state.

---

## IV. Architecture & Behavioral Feedback Loop

### 1. Incident Representation
For incident $i$, define:
$$I_i = (C_i, F_i, R_i, A_i, O_i, B_i, K_i)$$
Where:
- $C_i$: Context (telemetry, topology, load, configuration version)
- $F_i$: Observed failure (symptoms, exceptions, error codes)
- $R_i$: Root-cause hypothesis generated by RCA agent
- $A_i$: Action selected from allowlist
- $O_i$: Immediate outcome (execution success/failure, recovery status)
- $B_i$: Post-remediation behavior (stability, side effects, latency drift)
- $K_i$: Resulting knowledge update to evolution memory

### 2. Behavioral Preference Model
For an action $a$ under context $c$:
$$S(a, c) = \frac{N_{\text{success}}(a, c)}{N_{\text{attempts}}(a, c)}$$
Combined with sample size, recency, context similarity, confidence, and action risk.

### 3. Safety Boundary Invariant
Learning is **never** permitted to expand operational authority or bypass policy. Candidate actions remain strictly inside predefined allowlists, and high-impact actions require human approval.

---

## V. Evaluation Metrics (MVP1)

| Metric | Operational Definition | Research Purpose |
|---|---|---|
| **MTTD** | Failure onset to reliable detection | Detection responsiveness |
| **MTTR** | Incident confirmation to validated recovery | Recovery efficiency |
| **Diagnosis Accuracy** | Correct root cause / evaluated incidents | Diagnostic quality |
| **Remediation Success** | Successful recoveries / attempted actions | Action effectiveness |
| **Recurrence Rate** | Repeated failure after remediation | Longer-term stability |
| **Human Intervention** | Incidents requiring manual approval or action | Autonomy level |
| **Unsafe Remediation** | Actions violating safety criteria or causing adverse effects | Safety verification |
| **Adaptation Gain** | Change in outcome quality across repeated comparable trials | Core MVP1 measure |
| **Control-Plane Overhead** | Added CPU, memory, latency, and storage cost | Operational feasibility |

---

## VI. References
1. J. O. Kephart and D. M. Chess, "The vision of autonomic computing," *Computer*, vol. 36, no. 1, pp. 41–50, 2003.
2. M. Salehie and L. Tahvildari, "Self-adaptive software: Landscape and research challenges," *ACM Trans. Auton. Adapt. Syst.*, vol. 4, no. 2, 2009.
3. M. G. Hinchey et al., "Adaptive immunity for software: Towards autonomous self-healing systems," in *Proc. IEEE SANER*, 2021.
4. "Knowledge-based intelligent system for IT incident DevOps," in *Proc. IEEE AIOps*, 2023.
5. Y. Chen et al., "AIOpsLab: A holistic framework to evaluate AI agents for enabling autonomous clouds," *Proc. Mach. Learn. Syst.*, vol. 7, 2025.
6. S. S. M. et al., "Mining root cause knowledge from cloud service incident investigations for AIOps," in *Proc. IEEE/ACM ICSE-SEIP*, 2022.
7. G. M. Church, Y. Gao, and S. Kosuri, "Next-generation digital information storage in DNA," *Science*, vol. 337, no. 6102, p. 1628, 2012.
8. L. Ceze, J. Nivala, and K. Strauss, "Molecular digital data storage using DNA," *Nat. Rev. Genet.*, vol. 20, pp. 456–466, 2019.
9. D. Bar-Lev et al., "Scalable and robust DNA-based storage via coding theory and deep learning," *Nat. Mach. Intell.*, vol. 7, pp. 639–649, 2025.
10. C. Imburgia et al., "Random access and semantic search in DNA data storage enabled by Cas9 and machine-guided design," *Nat. Commun.*, vol. 16, Art. no. 6388, 2025.
