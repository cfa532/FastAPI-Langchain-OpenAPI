import threading
from contextlib import contextmanager
from typing import Any, Generator

import tiktoken
from langchain_community.callbacks.manager import openai_callback_var
from langchain_community.callbacks.openai_info import standardize_model_name, MODEL_COST_PER_1K_TOKENS, \
    get_openai_token_cost_for_model, OpenAICallbackHandler
from langchain_core.outputs import LLMResult

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

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Run when chain ends running."""
        text_response = response.generations[0][0].text
        encoding = tiktoken.get_encoding("cl100k_base")
        self.completion_tokens = len(encoding.encode(text_response))
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
            self.total_cost = prompt_cost + completion_cost
            # self.total_cost += prompt_cost + completion_cost
            self.total_tokens = self.prompt_tokens + self.completion_tokens
            self.successful_requests += 1


@contextmanager
def get_cost_tracker_callback(model_name) -> Generator[CostTrackerCallback, None, None]:
    cb = CostTrackerCallback(model_name)
    openai_callback_var.set(cb)
    yield cb
    openai_callback_var.set(None)
