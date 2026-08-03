"""Two-phase LLM summarization of daily news into top-5 topic lists.

Isolates the vLLM/torch dependency to inside ``run_llm_analysis`` (not at
module import time), so the rest of the pipeline -- and its unit tests --
can be imported on a machine without a GPU or the heavy
``requirements-pipeline.txt`` extras installed. This is the only module in
``pipeline/`` that needs a GPU.
"""

from __future__ import annotations

import logging

import pandas as pd

from pipeline.config import Config

logger = logging.getLogger(__name__)

_SUMMARY_SYSTEM_PROMPT = "You are a helpful summarizing assistant."

_TOPICS_TEMPLATE = """TASK:
Extract exactly 5 topics from the provided text.

RULES:
1. Output exactly five topics in a numbered list, no more and no less.
2. Use exactly one topic title and exactly one sentence for each topic.
3. Output MUST strictly follow the template below.
4. Use standard Markdown formatting.
5. NO introductory text, NO summary, NO concluding remarks, NO additional newlines.

TEMPLATE:
1. **Topic Title**: Sentence.
2. **Topic Title**: Sentence.
3. **Topic Title**: Sentence.
4. **Topic Title**: Sentence.
5. **Topic Title**: Sentence.

TEXT TO ANALYZE: {text}"""


class SummarizationError(RuntimeError):
    """Raised when the LLM engine can't be initialized or generation fails."""


def _chunk_text(text: str, chunk_size: int) -> list[str]:
    """Split text into fixed-size chunks, keeping the model's context window bounded."""
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)] or [""]


def run_llm_analysis(df_news: pd.DataFrame) -> pd.DataFrame:
    """Summarize each day's aggregated article text down to a 5-topic report.

    Two-phase map-reduce, matching the original notebook pipeline's
    approach: long daily text is chunked and summarized independently
    (phase 1), then a given day's chunk summaries are concatenated and
    reduced to the fixed 5-topic template (phase 2) -- keeping every
    prompt within the model's context window regardless of how much news
    a given day had.

    Returns a DataFrame with ``date``, ``tickers_count`` and
    ``top_5_topics`` columns, ready to write out via ``pipeline.run``.
    """
    try:
        from vllm import LLM, SamplingParams
    except ImportError as exc:
        raise SummarizationError(
            "vLLM is not installed. Summarization requires the GPU-only extras in "
            "requirements-pipeline.txt -- see pipeline/README.md."
        ) from exc

    logger.info("Initializing LLM engine (%s)...", Config.MODEL_ID)
    try:
        llm = LLM(
            model=Config.MODEL_ID,
            quantization="compressed-tensors",
            gpu_memory_utilization=Config.GPU_MEMORY_UTILIZATION,
            max_model_len=Config.MAX_MODEL_LEN,
            enforce_eager=True,
            trust_remote_code=True,
            disable_log_stats=True,
        )
    except Exception as exc:
        raise SummarizationError(f"Failed to initialize LLM engine {Config.MODEL_ID!r}: {exc}") from exc

    tokenizer = llm.get_tokenizer()
    chunk_params = SamplingParams(temperature=0, max_tokens=150)
    final_params = SamplingParams(temperature=0, max_tokens=350)

    def render(user_content: str) -> str:
        messages = [
            {"role": "system", "content": _SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    # Phase 1: per-chunk summaries.
    chunk_prompts: list[str] = []
    chunks_per_row: list[int] = []
    for text in df_news["body"]:
        chunks = _chunk_text(text, Config.CHUNK_SIZE)
        chunks_per_row.append(len(chunks))
        chunk_prompts.extend(render(f"Summarize this: {c}. Be concise") for c in chunks)

    logger.info("Generating summaries for %d chunks...", len(chunk_prompts))
    chunk_outputs = llm.generate(chunk_prompts, chunk_params, use_tqdm=True)
    inter_summaries = [o.outputs[0].text.strip() for o in chunk_outputs]

    # Phase 2: reduce each day's chunk summaries to a 5-topic report.
    final_prompts = []
    cursor = 0
    for count in chunks_per_row:
        combined = " ".join(inter_summaries[cursor : cursor + count])
        cursor += count
        final_prompts.append(render(_TOPICS_TEMPLATE.format(text=combined)))

    logger.info("Compiling final reports for %d days...", len(final_prompts))
    final_outputs = llm.generate(final_prompts, final_params, use_tqdm=True)

    return pd.DataFrame(
        {
            "date": df_news["published_on"].values,
            "tickers_count": df_news["tickers_dict"].values,
            "top_5_topics": [o.outputs[0].text.strip() for o in final_outputs],
        }
    )
