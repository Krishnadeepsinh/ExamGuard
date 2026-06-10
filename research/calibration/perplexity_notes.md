# Perplexity and Entropy Notes

Ollama logprobs support is model-dependent. ExamGuard AI v6 therefore treats logprobs as preferred but not guaranteed.

Fallback behavior:

- Try Ollama logprobs for answer text.
- If unavailable, compute sliding-window Shannon entropy.
- Store `ai_detection_method` as `logprobs` or `entropy`.
- Never silently return a zero score.
- If both signals are unavailable, Orchestrator continues with remaining factors.
