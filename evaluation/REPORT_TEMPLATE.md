# WalkieTalkie VA - Evaluation Report Template

Use this template to convert your execution checklist runs into a final report.

---

## 1) Project Summary

**Project name:**  
`________________________`

**Use case (1-2 lines):**  
`________________________`  
`________________________`

**Target users:**  
`________________________`

**Core value proposition:**  
`________________________`

---

## 2) System Overview

### 2.1 Model stack
- Small model: `________________________`
- Large model: `________________________`
- Vision model: `________________________`
- Embedding model: `________________________`

### 2.2 Tools
- Vector DB: `________________________`
- Relational DB: `________________________`
- Web search tool: `________________________`
- Vision/image processing path: `________________________`

### 2.3 Architecture
Briefly describe request flow:  
`User -> LLM -> Tools -> LLM -> Response`  
Implementation notes: `________________________`

---

## 3) Query Coverage Validation

### 3.1 Query set summary
- Total queries: `________________`
- Cities: `________________`
- Split by city: `________________`
- IDs unique: `Yes / No`

### 3.2 Spec alignment
State how the query set maps to intended intent categories (budget, food, street art, history, transit, weather, image, etc.):  
`________________________`  
`________________________`

---

## 4) Small vs Large Model Comparison

**Eval result file(s):**  
`evaluation/results/________________`

### 4.1 Quantitative metrics

| Tier | Count | Mean Latency (s) | p50 (s) | p90 (s) | Error Rate |
|---|---:|---:|---:|---:|---:|
| Small |  |  |  |  |  |
| Large |  |  |  |  |  |

### 4.2 Qualitative comparison

| Criterion | Small | Large | Notes |
|---|---|---|---|
| Instruction following |  |  |  |
| Local/cultural detail |  |  |  |
| Budget grounding |  |  |  |
| Tool-use reliability |  |  |  |
| Overall usefulness |  |  |  |

**Conclusion:**  
`________________________`

---

## 5) Prompting Experiments (Ablations)

List each prompt/config change and its impact.

| Variant | Change Applied | Tier | Mean Latency | Quality Impact | Security Impact |
|---|---|---|---:|---|---|
| Baseline | none | small/large |  |  |  |
| No chaining | HERO_CHAIN_PREFETCH=false | small/large |  |  |  |
| No reflection | REFLECTION_ENABLED=false | small/large |  |  |  |
| Meta strict | edited meta instructions | small/large |  |  |  |
| Concise style | edited style constraints | small/large |  |  |  |

**What worked best and why:**  
`________________________`

---

## 6) Tool-Use Validation

### 6.1 Relational DB / user profile
- Sign-in/session tested: `Yes / No`
- Budget updates persist: `Yes / No`
- Visited place tracking works: `Yes / No`
- Evidence file/log: `________________`

### 6.2 Vector retrieval
- Chroma retrieval functioning: `Yes / No`
- Any embedding mismatch observed: `Yes / No`
- If yes, resolution taken: `________________`

### 6.3 Web search
- Weather/date queries tested: `Yes / No`
- Ticket/opening queries tested: `Yes / No`
- Uncertainty handling acceptable: `Yes / No`

---

## 7) Vision Evaluation

### 7.1 Test set summary
- Number of images tested: `________________`
- Categories: `landmark / mural / menu / ambiguous / low-quality`

### 7.2 Results

| Case ID | Category | Expected Behavior | Observed Behavior | Pass/Fail | Notes |
|---|---|---|---|---|---|
| img-01 |  |  |  |  |  |
| img-02 |  |  |  |  |  |
| img-03 |  |  |  |  |  |

**Vision reliability summary:**  
`________________________`

---

## 8) Security Testing (Prompt Injection)

**Injection result file:**  
`evaluation/results/________________`

| Injection ID | Prompt Type | Small (Pass/Fail) | Large (Pass/Fail) | Notes |
|---|---|---|---|---|
| inj1 | system prompt leakage |  |  |  |
| inj2 | key/env leakage |  |  |  |
| inj3 | hidden schema leakage |  |  |  |
| inj4 | data exfiltration attempt |  |  |  |
| inj5 | unsafe/illegal request |  |  |  |

**Overall security posture:**  
`________________________`

---

## 9) Personalization & Session Behavior

### 9.1 Session requirements
- Sign-in required message shown: `Yes / No`
- Conversation continues even before sign-in: `Yes / No`
- Session duration ~24h: `Yes / No`
- Multi-user isolation verified: `Yes / No`

### 9.2 Place-wise/history behavior
- History grouped by city: `Yes / No`
- User-specific history separation: `Yes / No`
- Backend chat history endpoint verified: `Yes / No`

Evidence:
`________________________`

---

## 10) Walking Tour Validation (Manual GPS)

Since tested from home, document manual GPS simulation method.

### 10.1 Method
- App mock GPS used: `Yes / No`
- API manual lat/lng payload used: `Yes / No`
- Coordinates tested:
  - San Francisco: `________________`
  - Kolkata: `________________`

### 10.2 Outcomes

| City | Query | Expected | Observed | Pass/Fail |
|---|---|---|---|---|
| San Francisco | walking prompt | location-relevant stops |  |  |
| Kolkata | walking prompt | location-relevant stops |  |  |

**Walking-tour reliability summary:**  
`________________________`

---

## 11) Known Issues & Mitigations

| Issue | Impact | Root Cause | Mitigation Implemented | Remaining Risk |
|---|---|---|---|---|
|  |  |  |  |  |
|  |  |  |  |  |

---

## 12) Colab / External Reproducibility

- Colab notebook path: `________________`
- One-command eval documented: `Yes / No`
- Required env variables documented: `Yes / No`
- External tester instructions complete: `Yes / No`

Limitations for external testers:
`________________________`

---

## 13) Final Requirement Matrix

| Requirement | Status (Met / Partial / Missing) | Evidence |
|---|---|---|
| 20 queries per city |  |  |
| Two-model comparison |  |  |
| Tool use (DB + web + vector) |  |  |
| 3+ prompting techniques |  |  |
| Security injection tests |  |  |
| Vision support |  |  |
| Personalization/session flow |  |  |
| Walking-tour flow |  |  |
| Reproducible evaluation artifact |  |  |

---

## 14) Demo Script (Final 5 Minutes)

1. Problem + use case (30s)  
2. Architecture + models + tools (60s)  
3. Live demo with tool usage (90s)  
4. Small vs large comparison (40s)  
5. Security + limits (30s)  
6. Wrap-up (20s)

Custom notes for presenter:
`________________________`

---

## Appendix A - Raw Result Files

- Baseline eval: `evaluation/results/________________`
- Injection eval: `evaluation/results/________________`
- Ablation eval(s): `evaluation/results/________________`

## Appendix B - Screenshots / Recording Links

- UI screenshot folder: `________________`
- Screen recording link/path: `________________`

