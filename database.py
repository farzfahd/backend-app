from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

class Settings(BaseSettings):
  DATABASE_URL:str
  JWT_KEY: str
  ALGORITHM: str
  GEMINI_API_KEY1:str
  GEMINI_API_KEY2:str
  class Config:
    env_file = ".env"

setting = Settings()

engine = create_async_engine(
  setting.DATABASE_URL, 
  echo=True, 
  connect_args={
        "statement_cache_size": 0 
    }
)
AsyncSessionLokal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
  async with AsyncSessionLokal() as session:
    yield session