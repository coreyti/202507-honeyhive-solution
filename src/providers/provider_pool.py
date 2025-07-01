import asyncio
import random
import structlog
from typing import List, Optional

from providers.openrouter import OpenRouterProvider
from providers.base import LLMProvider

logger = structlog.get_logger()

class ProviderPool:
    def __init__(self):
        self.providers: List[LLMProvider] = []
        self.lock = asyncio.Lock()

    async def initialize(self):
        """Initialize all providers"""
        # Free models available on OpenRouter
        provider_configs = [
            {
                "model": "mistralai/mistral-small-3.2-24b-instruct:free",
                "display_name": "Mistral Small 3.2 24B"
            },
            {
                "model": "meta-llama/llama-4-scout:free",
                "display_name": "Meta Llama 4 Scout"
            },
            {
                "model": "meta-llama/llama-3.1-8b-instruct:free",
                "display_name": "Meta Llama 3.1 8B"
            },
            {
                "model": "google/gemma-2-9b-it:free",
                "display_name": "Google Gemma 2 9B"
            }
        ]

        for config in provider_configs:
            provider = OpenRouterProvider(
                model_name=config["model"],
                display_name=config["display_name"]
            )
            await provider.initialize()
            self.providers.append(provider)

        logger.info("Provider pool initialized", provider_count=len(self.providers))

    async def cleanup(self):
        """Cleanup all providers"""
        for provider in self.providers:
            await provider.cleanup()

    async def get_available_provider(self) -> Optional[LLMProvider]:
        """Get a healthy provider, preferring less loaded ones"""
        healthy_providers = [p for p in self.providers if p.is_healthy]
        
        if not healthy_providers:
            logger.error("No healthy providers available")
            return None

        # Sort by failure count (ascending) to prefer more reliable providers
        healthy_providers.sort(key=lambda p: p.failure_count)
        
        # Add some randomness among the best providers to distribute load
        best_providers = [p for p in healthy_providers if p.failure_count == healthy_providers[0].failure_count]
        
        selected = random.choice(best_providers)
        logger.debug("Selected provider", provider=selected.model_name)
        return selected

    async def get_healthy_providers(self) -> List[LLMProvider]:
        """Get all healthy providers"""
        return [p for p in self.providers if p.is_healthy]

    def mark_provider_failed(self, provider: LLMProvider):
        """Mark a provider as failed"""
        provider.mark_failure()
        logger.warning("Provider marked as failed", 
                      provider=provider.model_name, 
                      failure_count=provider.failure_count)

    async def health_check_all(self):
        """Run health checks on all providers"""
        async def check_provider(provider):
            try:
                is_healthy = await provider.health_check()
                logger.debug("Provider health check", 
                           provider=provider.model_name, 
                           healthy=is_healthy)
            except Exception as e:
                logger.error("Provider health check failed", 
                           provider=provider.model_name, 
                           error=str(e))

        await asyncio.gather(*[check_provider(p) for p in self.providers], return_exceptions=True)
