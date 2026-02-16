from pydantic import BaseSettings
class Settings(BaseSettings):
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db: str = "caps_ai"
    jwt_secret: str = "change_me"
    jwt_algorithm: str = "HS256"
    openai_api_key: str = ""
    similarity_threshold: float = 0.8
    class Config:
        env_file = ".env"
settings = Settings()
