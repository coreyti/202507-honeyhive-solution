from abc import ABC, abstractmethod
from typing import Optional

class LLMProvider(ABC):
    def __init__(self, model_name: str, api_key: str):
        self.model_name = model_name
        self.api_key = api_key
        self.is_healthy = True
        self.failure_count = 0
        self.max_failures = 3

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """Generate response from LLM"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is healthy"""
        pass

    def mark_failure(self):
        """Mark provider as failed"""
        self.failure_count += 1
        if self.failure_count >= self.max_failures:
            self.is_healthy = False

    def mark_success(self):
        """Mark provider as successful"""
        self.failure_count = 0
        self.is_healthy = True
