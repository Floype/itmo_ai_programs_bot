# config.py
import os
from pydantic import BaseModel, Field

class Settings(BaseModel):

    bot_token: str = "<8134278701:AAEN9PiCo-4BsdbsGpXxhrJZ3jlz8eR1COM>"

    program_urls: dict = {
        "ai": "https://abit.itmo.ru/program/master/ai",
        "ai_product": "https://abit.itmo.ru/program/master/ai_product",
    }
    data_dir: str = "data"

settings = Settings()
