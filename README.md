<p align="center">
  <h1 align="center">CrescendoGuard</h1>
  <p align="center">
    <strong>A Reproducible Defense Framework for Protecting Large Language Models Against Multi Turn Jailbreak Escalation</strong>
  </p>
  <p align="center">
    Built around Llama 3.2 3B Instruct · Rule Based Risk Detection · Layered Mitigation Pipeline
  </p>
</p>

<br/>

## Overview

CrescendoGuard is a research prototype that implements a comprehensive defense pipeline for protecting instruction following language models from Crescendo style multi turn jailbreak attacks. Unlike single prompt moderation systems, CrescendoGuard monitors the full conversational trajectory across turns, computes cumulative risk with exponential decay, and applies a layered sequence of mitigations that can block, rewrite, or replace content at each stage of the generation lifecycle.

The framework is designed around Llama 3.2 3B Instruct and ships with a deterministic dry run simulator that enables reproducible benchmarking without requiring GPU hardware or model access. The same defense pipeline can wrap the real Hugging Face Transformers model when hardware and access are available.

<br/>

## System Architecture

The following diagram presents the complete system architecture, illustrating how every component connects within the CrescendoGuard framework.

```mermaid
graph TB
    subgraph External["External Layer"]
        CLI["CLI Interface<br/>cli.py"]
        CFG["Policy Configuration<br/>default_policy.json"]
        ATK["Attack Vectors<br/>crescendo_attack_vectors.json"]
        BEN["Benign Controls<br/>benign_controls.json"]
    end

    subgraph Core["Core Defense Pipeline"]
        SP["SafetyPolicy<br/>Thresholds and Weights"]
        CD["CrescendoDetector<br/>Multi Signal Risk Scorer"]
        DP["DefensePipeline<br/>Turn Orchestrator"]
        BS["build_strategy()<br/>Strategy Factory"]
    end

    subgraph Mitigations["Mitigation Layer"]
        RG["RollingRiskGate<br/>Cumulative Risk Blocker"]
        CQ["ContextQuarantine<br/>Context Rewriter"]
        PV["PostResponseVerifier<br/>Output Scanner"]
    end

    subgraph Models["Model Layer"]
        MC["ModelClient Protocol<br/>Abstract Interface"]
        DR["DryRunLlamaModel<br/>Deterministic Simulator"]
        HF["HuggingFaceLlamaClient<br/>Real Model Adapter"]
    end

    subgraph Output["Benchmark and Reporting"]
        BM["Benchmark Engine<br/>benchmark.py"]
        RP["Report Generator<br/>reporting.py"]
        JSON["benchmark_results.json"]
        CSV["strategy_metrics.csv"]
        MD["benchmark_summary.md"]
        TR["technical_report.md"]
    end

    CLI --> BS
    CLI --> BM
    CFG --> SP
    ATK --> BM
    BEN --> BM

    SP --> CD
    SP --> RG
    SP --> CQ
    SP --> PV
    CD --> DP
    BS --> DP
    RG --> DP
    CQ --> DP
    PV --> DP

    MC --> DR
    MC --> HF
    DR --> DP
    HF --> DP

    BM --> DP
    BM --> RP
    BM --> JSON
    BM --> CSV
    BM --> MD
    RP --> TR

    style External fill:#1a1a2e,stroke:#16213e,color:#e2e8f0
    style Core fill:#0f3460,stroke:#533483,color:#e2e8f0
    style Mitigations fill:#533483,stroke:#e94560,color:#e2e8f0
    style Models fill:#16213e,stroke:#0f3460,color:#e2e8f0
    style Output fill:#1a1a2e,stroke:#533483,color:#e2e8f0
```

<br/>

## Defense Pipeline Workflow

The following flowchart illustrates the exact sequence of operations that CrescendoGuard performs for every single conversation turn, from the moment a user message arrives to the final response delivery.

```mermaid
flowchart TD
    A["🗣️ User Sends Message"] --> B["📊 CrescendoDetector.assess()"]

    B --> B1["Scan for Hazard Categories<br/>10 categories with regex patterns"]
    B1 --> B2["Detect Behavioral Signals<br/>Operationalization, Evasion,<br/>Roleplay, Obfuscation"]
    B2 --> B3["Check Memory Stacking<br/>References to prior context<br/>with existing risk categories"]
    B3 --> B4["Check Semantic Drift<br/>Escalation pattern across<br/>recent turn scores"]
    B4 --> B5["Apply Safety Research Discount<br/>Reduce score for defensive<br/>and educational framing"]
    B5 --> B6["Compute Cumulative Risk<br/>Exponential decay weighted<br/>sum across all turns"]
    B6 --> C["📋 RiskAssessment Generated<br/>turn_risk, cumulative_risk, action"]

    C --> D{{"Mitigation 1<br/>RollingRiskGate<br/>before_model()"}}
    D -->|"cumulative_risk ≥ 0.68<br/>ACTION: BLOCK"| E["🚫 Return Safe Refusal<br/>Model Never Called"]
    D -->|"cumulative_risk < 0.68<br/>ACTION: ALLOW"| F{{"Mitigation 2<br/>ContextQuarantine<br/>before_model()"}}

    F -->|"cumulative_risk ≥ 0.48<br/>ACTION: REWRITE"| G["🔄 Replace Full History<br/>with Safety Envelope"]
    F -->|"cumulative_risk < 0.48<br/>ACTION: ALLOW"| H["Pass Original Messages"]

    G --> I["🤖 Model.generate()<br/>LLM Produces Response"]
    H --> I

    I --> J{{"Mitigation 3<br/>PostResponseVerifier<br/>after_model()"}}
    J -->|"Unsafe patterns detected<br/>ACTION: REPLACE"| K["🔁 Replace with<br/>Safe Refusal"]
    J -->|"Response is clean<br/>ACTION: ALLOW"| L["✅ Return Response<br/>to User"]

    K --> L

    style A fill:#2196F3,stroke:#1565C0,color:#fff
    style E fill:#f44336,stroke:#c62828,color:#fff
    style L fill:#4CAF50,stroke:#2E7D32,color:#fff
    style K fill:#FF9800,stroke:#E65100,color:#fff
    style G fill:#9C27B0,stroke:#6A1B9A,color:#fff
    style I fill:#00BCD4,stroke:#00838F,color:#fff
```

<br/>

## Risk Detection Engine

The CrescendoDetector operates as a multi signal scoring engine. The diagram below shows the complete detection architecture, including all ten hazard categories and seven behavioral signal types that contribute to the final risk assessment.

```mermaid
flowchart LR
    subgraph Input["Input Processing"]
        UT["User Turn Text"]
        HI["Conversation History"]
    end

    subgraph HazardScanning["Hazard Category Scanning"]
        H1["Cyber Abuse<br/>weight: 0.34"]
        H2["Weapons<br/>weight: 0.36"]
        H3["Credential Theft<br/>weight: 0.35"]
        H4["Privacy Abuse<br/>weight: 0.32"]
        H5["Self Harm<br/>weight: 0.42"]
        H6["Financial Fraud<br/>weight: 0.34"]
        H7["Biosecurity<br/>weight: 0.40"]
        H8["Extremism<br/>weight: 0.36"]
        H9["Physical Intrusion<br/>weight: 0.32"]
        H10["Policy Evasion<br/>weight: 0.30"]
    end

    subgraph SignalDetection["Behavioral Signal Detection"]
        S1["Operationalization<br/>+0.22"]
        S2["Prompt Evasion<br/>+0.18"]
        S3["Roleplay Disguise<br/>+0.12"]
        S4["Memory Stacking<br/>+0.11"]
        S5["Semantic Drift<br/>+0.13"]
        S6["Obfuscation<br/>+0.10"]
        S7["Safety Research Context<br/>−0.11"]
    end

    subgraph RiskComputation["Risk Computation"]
        TS["Turn Score<br/>sum of matched weights"]
        CRS["Cumulative Risk Score<br/>exponential decay aggregation"]
        ACT{"Action Decision"}
    end

    subgraph Outcomes["Outcomes"]
        AL["ALLOW<br/>risk < 0.38"]
        RW["REWRITE<br/>risk ≥ 0.48"]
        BL["BLOCK<br/>risk ≥ 0.68"]
    end

    UT --> HazardScanning
    UT --> SignalDetection
    HI --> S4
    HI --> S5

    HazardScanning --> TS
    SignalDetection --> TS
    TS --> CRS
    CRS --> ACT

    ACT --> AL
    ACT --> RW
    ACT --> BL

    style Input fill:#263238,stroke:#37474F,color:#ECEFF1
    style HazardScanning fill:#1B5E20,stroke:#2E7D32,color:#E8F5E9
    style SignalDetection fill:#E65100,stroke:#F57C00,color:#FFF3E0
    style RiskComputation fill:#4A148C,stroke:#6A1B9A,color:#F3E5F5
    style Outcomes fill:#0D47A1,stroke:#1565C0,color:#E3F2FD
```

<br/>

## Class Structure

The following class diagram provides a complete view of all classes, their attributes, methods, and inheritance relationships within the CrescendoGuard framework.

```mermaid
classDiagram
    class ModelClient {
        <<Protocol>>
        +name: str
        +generate(messages: list) str
    }

    class DryRunLlamaModel {
        +name: str
        +unsafe_threshold: float
        +detector: CrescendoDetector
        +generate(messages: list) str
    }

    class HuggingFaceLlamaClient {
        +name: str
        +model_id: str
        +max_new_tokens: int
        +temperature: float
        +tokenizer: AutoTokenizer
        +model: AutoModelForCausalLM
        +generate(messages: list) str
    }

    class SafetyPolicy {
        +allow_threshold: float
        +rewrite_threshold: float
        +block_threshold: float
        +post_replace_threshold: float
        +risk_decay: float
        +turn_weight: float
        +max_evidence_items: int
        +category_weights: dict
        +signal_weights: dict
        +from_json(path) SafetyPolicy
    }

    class CrescendoDetector {
        +policy: SafetyPolicy
        +assess(history, user_text) RiskAssessment
        +response_is_unsafe(text, history) bool
    }

    class Mitigation {
        <<Abstract>>
        +name: str
        +before_model(messages, risk) MitigationDecision
        +after_model(messages, response, risk) MitigationDecision
    }

    class RollingRiskGate {
        +policy: SafetyPolicy
        +before_model(messages, risk) MitigationDecision
    }

    class ContextQuarantine {
        +policy: SafetyPolicy
        +before_model(messages, risk) MitigationDecision
    }

    class PostResponseVerifier {
        +policy: SafetyPolicy
        +detector: CrescendoDetector
        +after_model(messages, response, risk) MitigationDecision
    }

    class DefensePipeline {
        +model: ModelClient
        +detector: CrescendoDetector
        +mitigations: tuple
        +run_turn(history, user_text) GuardedResponse
    }

    class Message {
        +role: str
        +content: str
        +to_dict() dict
    }

    class SafetySignal {
        +name: str
        +score: float
        +reason: str
        +evidence: tuple
        +category: str
        +to_dict() dict
    }

    class RiskAssessment {
        +turn_risk: float
        +cumulative_risk: float
        +action: str
        +categories: dict
        +signals: tuple
        +summary: str
        +to_dict() dict
    }

    class MitigationDecision {
        +name: str
        +action: str
        +reason: str
        +transformed_messages: tuple
        +response: str
        +to_dict() dict
    }

    class GuardedResponse {
        +response: str
        +blocked: bool
        +unsafe_detected: bool
        +risk: RiskAssessment
        +decisions: tuple
        +guard_latency_ms: float
        +model_latency_ms: float
        +model_called: bool
        +to_dict() dict
    }

    ModelClient <|.. DryRunLlamaModel
    ModelClient <|.. HuggingFaceLlamaClient
    Mitigation <|-- RollingRiskGate
    Mitigation <|-- ContextQuarantine
    Mitigation <|-- PostResponseVerifier

    DefensePipeline --> ModelClient
    DefensePipeline --> CrescendoDetector
    DefensePipeline --> Mitigation
    CrescendoDetector --> SafetyPolicy
    RollingRiskGate --> SafetyPolicy
    ContextQuarantine --> SafetyPolicy
    PostResponseVerifier --> SafetyPolicy
    PostResponseVerifier --> CrescendoDetector
    DefensePipeline ..> GuardedResponse
    CrescendoDetector ..> RiskAssessment
    CrescendoDetector ..> SafetySignal
```

<br/>

## Layered Defense Strategy

The layered strategy combines all three mitigations in a deliberate sequence. This diagram visualizes the chaining logic and shows exactly how each layer interacts to provide defense in depth.

```mermaid
flowchart TD
    subgraph Layer1["Layer 1: Rolling Risk Gate"]
        direction TB
        L1A["Evaluate cumulative_risk against block_threshold 0.68"]
        L1B{"cumulative_risk ≥ 0.68?"}
        L1C["🚫 BLOCK<br/>Return safe refusal immediately<br/>Model is never invoked"]
        L1D["✅ ALLOW<br/>Proceed to next layer"]
        L1A --> L1B
        L1B -->|Yes| L1C
        L1B -->|No| L1D
    end

    subgraph Layer2["Layer 2: Context Quarantine"]
        direction TB
        L2A["Evaluate cumulative_risk against rewrite_threshold 0.48"]
        L2B{"cumulative_risk ≥ 0.48?"}
        L2C["🔄 REWRITE<br/>Replace conversation with<br/>safety envelope containing<br/>risk categories and<br/>benign response directive"]
        L2D["✅ ALLOW<br/>Pass original conversation"]
        L2A --> L2B
        L2B -->|Yes| L2C
        L2B -->|No| L2D
    end

    subgraph ModelGen["Model Generation"]
        MG["🤖 ModelClient.generate()<br/>Produce response from<br/>original or rewritten context"]
    end

    subgraph Layer3["Layer 3: Post Response Verifier"]
        direction TB
        L3A["Scan model output for unsafe patterns<br/>and run response_is_unsafe() check"]
        L3B{"Unsafe content detected?"}
        L3C["🔁 REPLACE<br/>Substitute with safe refusal"]
        L3D["✅ ALLOW<br/>Deliver original response"]
        L3A --> L3B
        L3B -->|Yes| L3C
        L3B -->|No| L3D
    end

    L1D --> Layer2
    L2C --> ModelGen
    L2D --> ModelGen
    ModelGen --> Layer3

    style Layer1 fill:#1B5E20,stroke:#4CAF50,color:#E8F5E9
    style Layer2 fill:#4A148C,stroke:#9C27B0,color:#F3E5F5
    style ModelGen fill:#0D47A1,stroke:#2196F3,color:#E3F2FD
    style Layer3 fill:#BF360C,stroke:#FF5722,color:#FBE9E7
```

<br/>

## Benchmark Execution Workflow

The benchmark engine orchestrates a full evaluation across all defense strategies. The following diagram shows how attack scenarios and benign controls flow through the system to produce the final metrics and reports.

```mermaid
flowchart TD
    START["📂 CLI: run_benchmark command"] --> LOAD["Load Scenarios<br/>10 Attack Vectors + 5 Benign Controls"]
    LOAD --> POLICY["Load SafetyPolicy<br/>from configs/default_policy.json"]
    POLICY --> DET["Initialize CrescendoDetector"]
    DET --> LOOP["For each strategy:<br/>none, rolling_gate, context_quarantine,<br/>post_guard, layered"]

    LOOP --> BUILD["build_strategy()<br/>Construct DefensePipeline<br/>with appropriate mitigations"]
    BUILD --> ATTACKS["Run all 10 attack scenarios"]
    BUILD --> CONTROLS["Run all 5 benign controls"]

    ATTACKS --> SCENARIO["For each scenario"]
    CONTROLS --> SCENARIO

    SCENARIO --> TURNS["Execute each turn sequentially<br/>Turn 1 → Turn 2 → Turn 3"]
    TURNS --> PIPELINE["DefensePipeline.run_turn()<br/>Detect → Mitigate → Generate → Verify"]
    PIPELINE --> RECORD["Record per turn metrics:<br/>risk scores, decisions,<br/>latency, response preview"]
    RECORD --> SCENARIO

    SCENARIO --> METRICS["Compute Strategy Metrics<br/>ASR, Intercept Rate,<br/>Control Block Rate,<br/>Guard Latency"]

    METRICS --> LOOP

    LOOP --> OUTPUT["Write Output Artifacts"]
    OUTPUT --> O1["📄 benchmark_results.json<br/>Complete per turn data"]
    OUTPUT --> O2["📊 strategy_metrics.csv<br/>Aggregate strategy comparison"]
    OUTPUT --> O3["📝 benchmark_summary.md<br/>Markdown formatted results"]
    OUTPUT --> O4["📖 technical_report.md<br/>Full research report"]

    style START fill:#2196F3,stroke:#1565C0,color:#fff
    style OUTPUT fill:#4CAF50,stroke:#2E7D32,color:#fff
    style PIPELINE fill:#9C27B0,stroke:#6A1B9A,color:#fff
```

<br/>

## Cumulative Risk Scoring Model

The following diagram illustrates how the cumulative risk score evolves across conversation turns using exponential decay. This is the mathematical core of the detection engine that distinguishes Crescendo attacks from benign conversations.

```mermaid
flowchart LR
    subgraph Turn1["Turn 1: Benign Setup"]
        T1S["Score: 0.12<br/>Educational framing"]
        T1C["Cumulative: 0.12"]
    end

    subgraph Turn2["Turn 2: Bridging"]
        T2D["Prior × decay 0.72"]
        T2S["Score: 0.35<br/>Operational language"]
        T2C["Cumulative: 0.44"]
    end

    subgraph Turn3["Turn 3: Escalation"]
        T3D["Prior × decay 0.72"]
        T3S["Score: 0.62<br/>Hazard + memory stacking"]
        T3C["Cumulative: 0.94"]
    end

    subgraph Decision["Action Decision"]
        THR{"Threshold Check"}
        BLK["🚫 BLOCK<br/>0.94 ≥ 0.68"]
    end

    T1S --> T1C
    T1C --> T2D
    T2D --> T2S
    T2S --> T2C
    T2C --> T3D
    T3D --> T3S
    T3S --> T3C
    T3C --> THR
    THR --> BLK

    style Turn1 fill:#1B5E20,stroke:#4CAF50,color:#E8F5E9
    style Turn2 fill:#F57F17,stroke:#FBC02D,color:#212121
    style Turn3 fill:#B71C1C,stroke:#F44336,color:#FFEBEE
    style Decision fill:#4A148C,stroke:#9C27B0,color:#F3E5F5
```

<br/>

## Project Layout

```text
crescendo/
├── configs/
│   └── default_policy.json            Guard thresholds and scoring weights
├── data/
│   ├── crescendo_attack_vectors.json  Sanitized 10 vector benchmark suite
│   └── benign_controls.json           Benign multi turn control conversations
├── src/
│   └── crescendo_guard/
│       ├── __init__.py                Package exports
│       ├── benchmark.py               Benchmark engine and scenario runner
│       ├── cli.py                     Command line interface
│       ├── detectors.py               Multi signal risk detection engine
│       ├── mitigations.py             Three mitigation implementations
│       ├── model_clients.py           Model client protocol and adapters
│       ├── pipeline.py                Core defense pipeline orchestrator
│       ├── policy.py                  Safety policy configuration
│       ├── reporting.py               Technical report generator
│       └── types.py                   Data structures and type definitions
├── tests/
│   ├── conftest.py                    Shared test fixtures
│   ├── test_benchmark.py             Benchmark behavior tests
│   ├── test_detector.py              Detector unit tests
│   └── test_pipeline.py              Pipeline integration tests
├── results/                           Generated benchmark outputs
├── reports/                           Generated technical report
├── docs/
│   └── threat_model.md               Evaluation assumptions and attacker model
├── .github/
│   └── workflows/
│       └── ci.yml                     Continuous integration workflow
├── LICENSE                            MIT License
├── SAFETY.md                          Safety and responsible use guidelines
└── pyproject.toml                     Package configuration and dependencies
```

<br/>

## What Is Included

**Three Defense Strategies** implemented as pluggable mitigation components that can be composed in any combination:

| Strategy | Mechanism | When It Acts |
|---|---|---|
| Rolling Risk Gate | Cumulative risk scoring with exponential decay | Before model generation |
| Context Quarantine | High risk context compression into a safety envelope | Before model generation |
| Post Response Verifier | Output scanning for unsafe completion markers | After model generation |

**A Layered Strategy** that combines all three mitigations in sequence for defense in depth.

**Ten Sanitized Attack Vectors** covering cyber abuse, weapons, credential theft, privacy abuse, self harm, financial fraud, biosecurity, extremism, physical intrusion, and policy evasion.

**Five Benign Control Conversations** for estimating the false positive rate on legitimate safety discussions.

**A Complete Benchmark Suite** that produces JSON results, CSV metrics, a Markdown summary, and a full technical report.

**Unit Tests** for the detector, pipeline, and benchmark behavior.

**Optional Real Model Adapter** for `meta-llama/Llama-3.2-3B-Instruct` via Hugging Face Transformers.

**A CI Workflow, Threat Model, and Safety Notes** for responsible research publication.

<br/>

## Quick Start

```powershell
git clone https://github.com/RajatRawal-06/Crescendo.git
cd Crescendo
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
python -m crescendo_guard.cli run-benchmark
python -m unittest discover -s tests
```

The benchmark artifacts are written to `results/` and `reports/`.

<br/>

## Run the Benchmark

```powershell
python -m crescendo_guard.cli run-benchmark --results-dir results
```

Expected high level outcome with the deterministic simulator:

| Strategy | Expected ASR | Behavior |
|---|---|---|
| none | 100% | No guard is active so every attack succeeds |
| rolling_gate | 20% | Blocks late stage escalation via cumulative scoring |
| context_quarantine | 0% | Eliminates model exposure to risky conversational history |
| post_guard | 0% | Catches unsafe outputs after generation |
| layered | 0% | Drives ASR to zero while preserving benign controls |

<br/>

## Wrap the Real Llama Model

Llama 3.2 3B Instruct is gated on Hugging Face, so first accept the model terms and configure an `HF_TOKEN` with access.

```powershell
python -m pip install -e .[llama]
$env:HF_TOKEN="hf_..."
python -m crescendo_guard.cli run-benchmark --model hf --max-new-tokens 160
```

The Hugging Face model card documents the `meta-llama/Llama-3.2-3B-Instruct` model identifier, Transformers usage, license, and access gating: <https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct>.

<br/>

## Safety Notes

This project is defensive research. Attack vectors are written as non actionable scenario prompts, and the simulator never emits procedural harmful content. When using a real model, run the benchmark only in a controlled research environment and review any generated logs before sharing.

See `SAFETY.md` and `docs/threat_model.md` for the repository safety posture and evaluation assumptions.

<br/>

## References

1. Russinovich, Salem, and Eldan, "Great, Now Write an Article About That: The Crescendo Multi Turn LLM Jailbreak Attack", arXiv:2404.01833: <https://arxiv.org/abs/2404.01833>
2. Meta Llama 3.2 3B Instruct model card: <https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct>
3. Argilla DPO Mix 7K dataset card: <https://huggingface.co/datasets/argilla/dpo-mix-7k>

<br/>

## License

This project is licensed under the MIT License. See `LICENSE` for details.
