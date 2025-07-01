import aiohttp
import asyncio
import structlog
from typing import Dict, Any, Optional

from core.config import settings
from providers.base import LLMProvider

logger = structlog.get_logger()

class OpenRouterProvider(LLMProvider):
    def __init__(self, model_name: str, display_name: str):
        super().__init__(model_name, settings.OPENROUTER_API_KEY)
        self.display_name = display_name
        self.base_url = settings.OPENROUTER_BASE_URL
        self.session: Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        """Initialize HTTP session"""
        timeout = aiohttp.ClientTimeout(total=settings.LLM_TIMEOUT)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://llm-evaluation-service",
                "X-Title": "LLM Evaluation Service"
            }
        )

    async def cleanup(self):
        """Cleanup HTTP session"""
        if self.session:
            await self.session.close()

    async def generate(self, prompt: str) -> str:
        """Generate response using OpenRouter API"""
        if not self.session:
            await self.initialize()

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1000,
            "temperature": 0.1,  # Low temperature for consistent evaluation
            "top_p": 0.9,
            "stream": False
        }

        try:
            async with self.session.post(f"{self.base_url}/chat/completions", json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data["choices"][0]["message"]["content"]
                    self.mark_success()
                    return content
                elif response.status == 429:
                    # Rate limited
                    logger.warning("OpenRouter rate limited", model=self.model_name)
                    raise Exception("Rate limited by OpenRouter")
                else:
                    error_text = await response.text()
                    logger.error("OpenRouter API error", 
                               status=response.status, 
                               error=error_text,
                               model=self.model_name)
                    raise Exception(f"OpenRouter API error: {response.status}")

        except asyncio.TimeoutError:
            logger.error("OpenRouter request timeout", model=self.model_name)
            self.mark_failure()
            raise Exception("Request timeout")
        except Exception as e:
            logger.error("OpenRouter request failed", model=self.model_name, error=str(e))
            self.mark_failure()
            raise

    async def health_check(self) -> bool:
        """Check provider health with a simple request"""
        try:
            if not self.session:
                await self.initialize()

            # Simple health check request
            payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10
            }

            async with self.session.post(f"{self.base_url}/chat/completions", json=payload) as response:
                if response.status == 200:
                    self.is_healthy = True
                    return True
                else:
                    self.is_healthy = False
                    return False

        except Exception as e:
            logger.error("Health check failed", model=self.model_name, error=str(e))
            self.is_healthy = False
            return False
