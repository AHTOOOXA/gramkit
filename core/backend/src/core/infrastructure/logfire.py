import logfire


def setup_logfire(write_token: str, environment: str):
    """Initialize Logfire with configuration."""
    logfire.configure(token=write_token, environment=environment, send_to_logfire="if-token-present")
    logfire.instrument_pydantic_ai()
    logfire.info("Hello, {place}!", place="World")
