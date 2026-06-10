# ExamGuard AI - 10 Agent Reference

Each agent is a named node in the planned LangGraph StateGraph. Judges should be able to open `backend/agents/graph.py` and verify the full topology.

| Agent | File | Trigger | Key Decision |
| --- | --- | --- | --- |
| Paper Config | `backend/agents/paper_config_agent.py` | `POST /paper-config` | Validates marks, chapters, join code |
| Material Ingestion | `backend/agents/material_ingestion_agent.py` | `POST /materials/upload` | OCR, chunking, chapter map |
| Orchestrator | `backend/agents/orchestrator_agent.py` | Every event | Deterministic CLEAN/WATCH/WARN/FLAGGED |
| Question Generation | `backend/agents/question_agent.py` | `POST /activate` | RAG plus Bloom prompts |
| Proctoring | `backend/agents/proctoring_agent.py` | Browser event | Event aggregation |
| Stylometric | `backend/agents/stylometric_agent.py` | Answer submit | Tier 1/2/3 baseline handling |
| Security | `backend/agents/security_agent.py` | Answer submit | Logprobs or entropy scoring |
| Evaluation | `backend/agents/evaluation_agent.py` | Session end | Objective and rubric grading |
| Report | `backend/agents/report_agent.py` | Report generate | PDF outline and signed URL contract |
| Review | `backend/agents/review_agent.py` | FLAGGED trigger | Appeal and grade release |

## LangGraph Topology

`backend/agents/graph.py` contains the node IDs and edges. The Orchestrator remains deterministic; LLMs may write explanations, but they do not decide escalation.
