# ReleaseSeal — Part B v3 audit results (40 public models)

> Evidence, not certification. A finding points at a place to check.

Captured 2026-11-08, aligned verifier (gpai-eu-v3), metadata only. 40/40 snapshotted, 0 errors, 0 zero-finding.

## Missing-documentation counts by item

| item | models missing |
|---|---|
| `cop.copyright_policy` | 40/40 |
| `cop.training_content_summary` | 38/40 |
| `xi.compute` | 34/40 |
| `xi.energy` | 33/40 |
| `xi.testing_process` | 30/40 |
| `cop.distribution` | 26/40 |
| `xii.acceptable_use` | 21/40 |
| `xii.downstream_integration` | 19/40 |
| `xi.evaluation_results` | 14/40 |
| `xi.intended_use` | 13/40 |
| `xii.io_modality` | 7/40 |
| `xi.data_summary` | 6/40 |

## Per-model finding counts

| model | license | findings | by class |
|---|---|---|---|
| `Qwen/Qwen2.5-0.5B` | apache-2.0 | 12 | V2×1 V4×10 V6×1 |
| `Qwen/Qwen2.5-0.5B-Instruct` | apache-2.0 | 11 | V2×1 V4×9 V6×1 |
| `Qwen/Qwen2.5-Coder-0.5B` | apache-2.0 | 11 | V2×1 V4×9 V6×1 |
| `Qwen/Qwen2.5-1.5B` | apache-2.0 | 12 | V2×1 V4×10 V6×1 |
| `microsoft/phi-2` | mit | 8 | V2×1 V4×7 |
| `microsoft/Phi-3-mini-4k-instruct` | mit | 6 | V4×6 |
| `TinyLlama/TinyLlama-1.1B-Chat-v1.0` | apache-2.0 | 9 | V4×9 |
| `HuggingFaceTB/SmolLM2-135M` | apache-2.0 | 10 | V2×1 V4×9 |
| `HuggingFaceTB/SmolLM2-360M` | apache-2.0 | 9 | V2×1 V4×8 |
| `HuggingFaceTB/SmolLM-1.7B` | apache-2.0 | 8 | V4×8 |
| `stabilityai/stablelm-2-1_6b` | other | 9 | V4×9 |
| `stabilityai/stablelm-3b-4e1t` | cc-by-sa-4.0 | 8 | V4×8 |
| `EleutherAI/pythia-70m` | apache-2.0 | 7 | V2×1 V4×6 |
| `EleutherAI/pythia-160m` | apache-2.0 | 7 | V2×1 V4×6 |
| `EleutherAI/gpt-neo-125m` | mit | 8 | V4×8 |
| `bigscience/bloom-560m` | bigscience-bloom-rail-1.0 | 4 | V4×3 V6×1 |
| `bigscience/bloomz-560m` | bigscience-bloom-rail-1.0 | 8 | V4×8 |
| `facebook/opt-125m` | other | 7 | V2×1 V4×6 |
| `facebook/opt-1.3b` | other | 7 | V2×1 V4×6 |
| `Salesforce/codegen-350M-mono` | bsd-3-clause | 4 | V4×4 |
| `google/flan-t5-base` | apache-2.0 | 6 | V4×6 |
| `google-t5/t5-small` | apache-2.0 | 7 | V4×7 |
| `distilbert/distilbert-base-uncased` | apache-2.0 | 6 | V4×6 |
| `google-bert/bert-base-uncased` | apache-2.0 | 7 | V4×7 |
| `FacebookAI/roberta-base` | mit | 7 | V4×7 |
| `openai-community/gpt2` | mit | 5 | V4×5 |
| `openai-community/gpt2-medium` | mit | 3 | V4×3 |
| `distilbert/distilgpt2` | apache-2.0 | 3 | V4×3 |
| `deepseek-ai/deepseek-coder-1.3b-base` | other | 9 | V4×9 |
| `01-ai/Yi-6B` | apache-2.0 | 3 | V2×1 V4×2 |
| `tiiuae/falcon-rw-1b` | apache-2.0 | 10 | V2×1 V4×9 |
| `tiiuae/falcon-7b` | apache-2.0 | 8 | V4×8 |
| `bigcode/starcoder2-3b` | bigcode-openrail-m | 9 | V2×1 V4×8 |
| `sentence-transformers/all-MiniLM-L6-v2` | apache-2.0 | 7 | V4×7 |
| `microsoft/deberta-v3-base` | mit | 12 | V2×1 V4×11 |
| `cardiffnlp/twitter-roberta-base-sentiment-latest` | cc-by-4.0 | 10 | V4×10 |
| `mistralai/Mistral-7B-v0.1` | apache-2.0 | 12 | V4×12 |
| `google/gemma-2-2b` | gemma | 4 | V4×4 |
| `meta-llama/Llama-3.2-1B` | llama3.2 | 2 | V4×2 |
| `allenai/OLMo-1B-hf` | apache-2.0 | 7 | V2×1 V4×6 |

Gated disclosure: `google/gemma-2-2b` and `meta-llama/Llama-3.2-1B` are gated; their config could not be fetched, so inspection was card-metadata only.

Representative hash-chained evidence packs are in `packs/`; re-verify any offline with `releaseseal verify-pack <pack.json>`.
