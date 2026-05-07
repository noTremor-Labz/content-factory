from functools import lru_cache

from content_factory_pipeline.providers import ProviderRegistry, build_provider_registry


@lru_cache(maxsize=1)
def get_provider_registry() -> ProviderRegistry:
    return build_provider_registry()
