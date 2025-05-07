from datetime import datetime
import asyncio
from openai import OpenAI,AsyncOpenAI
import json
import time
from config import SummaryLLMConfig
import httpx



is_fake = False

async def call_api(messages: list) -> str:
    if is_fake:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8088/fakellm")
            result_string = response.text
            return result_string
    

    else:
        client = AsyncOpenAI(
            api_key = SummaryLLMConfig.API_KEY,
            base_url = SummaryLLMConfig.BASE_URL
            )
        model_id = SummaryLLMConfig.MODEL_ID
        #print("Model id:", model_id)
        completion = await client.chat.completions.create(
            model = model_id,
            messages = messages,
            temperature = SummaryLLMConfig.TEMPERATURE,
            max_tokens = SummaryLLMConfig.MAXTOKENS,
            stream = False
            )
        result_string = completion.choices[0].message.content
        return result_string


def convert_to_json(json_string: str) -> dict:    
    json_str = json_string.strip().strip('```json').strip('```').strip()
    data = json.loads(json_str)    
    return data
