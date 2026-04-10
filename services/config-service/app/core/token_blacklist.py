"""Service-level token blacklist wiring."""

from rag_config_common.auth.token_blacklist import TokenBlacklist

from app.core.settings import settings

token_blacklist = TokenBlacklist(settings.REDIS_URL)
