from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ANTHROPIC_API_KEY: str
    DATABASE_URL: str
    REDIS_URL: str
    ENVIRONMENT: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# For calling the settings
# is settings = Settings() and then you can access the variables like settings.ANTHROPIC_API_KEY, settings.DATABASE_URL, etc.
# print(settings.ANTHROPIC_API_KEY) That way can get access to the environment variables defined in the .env file.
