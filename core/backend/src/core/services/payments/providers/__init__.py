from core.domain.products import ProductCatalog
from core.infrastructure.database.models.enums import PaymentProvider
from core.services.payments.providers.telegram_stars import TelegramStarsProvider
from core.services.payments.providers.yookassa import YooKassaProvider
from core.services.payments.types import PaymentProviderInterface


def get_provider(provider_id: PaymentProvider, repo, services, products: ProductCatalog) -> PaymentProviderInterface:
    """
    Factory function to get the appropriate payment provider implementation.

    Config is read from settings by each provider.

    Args:
        provider_id: The ID of the provider to get
        repo: The repository for data access
        services: The services container
        products: App-specific products catalog (satisfies ProductCatalog protocol)

    Returns:
        Provider implementation instance
    """
    providers = {
        PaymentProvider.YOOKASSA: YooKassaProvider,
        PaymentProvider.TELEGRAM_STARS: TelegramStarsProvider,
        # Add more providers as needed
    }

    provider_class = providers.get(provider_id)
    if not provider_class:
        raise ValueError(f"Provider {provider_id} not supported")

    return provider_class(repo, services, products)
