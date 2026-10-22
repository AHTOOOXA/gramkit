import logfire


def setup_logfire(write_token: str, environment: str, service_version: str = ""):
    """Initialize Logfire with configuration."""
    logfire.configure(
        token=write_token,
        environment=environment,
        service_version=service_version or None,
        send_to_logfire="if-token-present",
    )
    logfire.instrument_pydantic_ai()
