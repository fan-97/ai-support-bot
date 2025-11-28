import httpx
import logging
from config.settings import OPENROUTER_API_KEY, OPENROUTER_BASE_URL

class OpenRouterService:
    _models_cache = []

    @classmethod
    async def fetch_models(cls):
        """Fetch all available models from OpenRouter."""
        if cls._models_cache:
            return cls._models_cache

        url = f"{OPENROUTER_BASE_URL}/models/user"
        headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                cls._models_cache = data.get('data', [])
                return cls._models_cache
        except Exception as e:
            logging.error(f"Failed to fetch models: {e}")
            return []

    @classmethod
    async def get_providers(cls):
        """Extract unique providers from model IDs (prefix before /)."""
        models = await cls.fetch_models()
        providers = set()
        for m in models:
            mid = m.get('id', '')
            if '/' in mid:
                providers.add(mid.split('/')[0])
            else:
                providers.add('other')
        return sorted(list(providers))

    @classmethod
    async def get_models_by_provider(cls, provider):
        """Get all models for a specific provider."""
        models = await cls.fetch_models()
        result = []
        for m in models:
            mid = m.get('id', '')
            p = mid.split('/')[0] if '/' in mid else 'other'
            if p == provider:
                result.append(m)
        return sorted(result, key=lambda x: x.get('name', ''))

    @classmethod
    async def get_model_details(cls, model_id):
        """Get details for a specific model."""
        models = await cls.fetch_models()
        for m in models:
            if m.get('id') == model_id:
                return m
        return None
