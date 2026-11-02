import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    env: str
    token: str
    test_guild_id: int | None


def load_config() -> Config:
    env = os.environ.get("APP_ENV", "dev")
    if env not in ("dev", "prod"):
        raise SystemExit(f"APP_ENV must be 'dev' or 'prod', got {env!r}")

    # Real environment variables (e.g. injected by the host) win over the file.
    load_dotenv(f".env.{env}", override=False)

    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise SystemExit(f"DISCORD_TOKEN is not set (looked in env and .env.{env})")

    guild = os.environ.get("TEST_GUILD_ID")
    return Config(env=env, token=token, test_guild_id=int(guild) if guild else None)
