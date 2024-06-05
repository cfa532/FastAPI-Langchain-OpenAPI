import threading
from contextlib import contextmanager
from typing import Any, Generator

import tiktoken
from langchain_community.callbacks.manager import openai_callback_var
from langchain_community.callbacks.openai_info import MODEL_COST_PER_1K_TOKENS, OpenAICallbackHandler
from langchain_core.outputs import LLMResult

MODEL_COST_PER_1K_TOKENS = MODEL_COST_PER_1K_TOKENS | {
    # GPT-4 input
    "gpt-4-turbo": 0.01,
    "gpt-4o": 0.005,

    # GPT-4 output
    "gpt-4-turbo-completion": 0.03,
    "gpt-4o-completion": 0.015,
}

def standardize_model_name(
    model_name: str,
    is_completion: bool = False,
) -> str:
    """
    Standardize the model name to a format that can be used in the OpenAI API.
    Args:
        model_name: Model name to standardize.
        is_completion: Whether the model is used for completion or not.
            Defaults to False.
    Returns:
        Standardized model name.

    """
    model_name = model_name.lower()
    if ".ft-" in model_name:
        model_name = model_name.split(".ft-")[0] + "-azure-finetuned"
    if ":ft-" in model_name:
        model_name = model_name.split(":")[0] + "-finetuned-legacy"
    if "ft:" in model_name:
        model_name = model_name.split(":")[1] + "-finetuned"
    if is_completion and (
        model_name.startswith("gpt-4")
        # or model_name.startswith("gpt-4o")
        or model_name.startswith("gpt-3.5")
        or model_name.startswith("gpt-35")
        or ("finetuned" in model_name and "legacy" not in model_name)
    ):
        return model_name + "-completion"
    else:
        return model_name

def get_openai_token_cost_for_model(
    model_name: str, num_tokens: int, is_completion: bool = False
) -> float:
    """
    Get the cost in USD for a given model and number of tokens.

    Args:
        model_name: Name of the model
        num_tokens: Number of tokens.
        is_completion: Whether the model is used for completion or not.
            Defaults to False.

    Returns:
        Cost in USD.
    """
    model_name = standardize_model_name(model_name, is_completion=is_completion)
    if model_name not in MODEL_COST_PER_1K_TOKENS:
        raise ValueError(
            f"Unknown model: {model_name}. Please provide a valid OpenAI model name."
            "Known models are: " + ", ".join(MODEL_COST_PER_1K_TOKENS.keys())
        )
    return MODEL_COST_PER_1K_TOKENS[model_name] * (num_tokens / 1000)

class CostTrackerCallback(OpenAICallbackHandler):

    def __init__(self, model_name: str) -> None:
        super().__init__()
        self.model_name = model_name
        self._lock = threading.Lock()

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        **kwargs: Any,
    ) -> None:
        encoding = tiktoken.get_encoding("cl100k_base")
        prompts_string = ''.join(prompts)
        self.prompt_tokens = len(encoding.encode(prompts_string))
        self.completion_tokens = 0

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        self.completion_tokens += 1

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Run when chain ends running."""
        # text_response = response.generations[0][0].text
        # encoding = tiktoken.get_encoding("cl100k_base")
        # self.completion_tokens = len(encoding.encode(text_response))
        model_name = standardize_model_name(self.model_name)
        if model_name in MODEL_COST_PER_1K_TOKENS:
            completion_cost = get_openai_token_cost_for_model(
                model_name, self.completion_tokens, is_completion=True
            )
            prompt_cost = get_openai_token_cost_for_model(model_name, self.prompt_tokens)
        else:
            completion_cost = 0
            prompt_cost = 0

        # update shared state behind lock
        with self._lock:
            self.total_cost += prompt_cost + completion_cost
            self.total_tokens = self.prompt_tokens + self.completion_tokens
            self.successful_requests += 1


@contextmanager
def get_cost_tracker_callback(model_name) -> Generator[CostTrackerCallback, None, None]:
    cb = CostTrackerCallback(model_name)
    openai_callback_var.set(cb)
    yield cb
    openai_callback_var.set(None)
