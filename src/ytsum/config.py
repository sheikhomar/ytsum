from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    OPEN_AI_API_KEY: str = Field(env="OPEN_AI_API_KEY")
    WEAK_MODEL_NAME: str = Field(env="WEAK_MODEL_NAME")
    STRONG_MODEL_NAME: str = Field(env="STRONG_MODEL_NAME")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


class InvalidSettingsError(RuntimeError):
    pass


def init_settings() -> Settings:
    """Initialize the application settings."""

    try:
        settings = Settings()
        return settings
    except ValidationError as e:
        msg = (
            "Error loading configuration. Please check that you have a `.env` file "
            "in the root directory of this project, and that it contains the "
            "corrent variables. Remember to follow the `.env.template` file.\n\n"
            f"Error details: {e}"
        )
        raise InvalidSettingsError(msg)
