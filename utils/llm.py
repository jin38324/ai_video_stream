from datetime import datetime
import asyncio
from openai import OpenAI,AsyncOpenAI
import json
import time
from config import LLMConfig
import httpx

client = AsyncOpenAI(
    api_key = LLMConfig.API_KEY,
    base_url = LLMConfig.BASE_URL
    )

is_fake = True

async def call_api(messages: list) -> str:
    if is_fake:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8088/fakellm")
            result_string = response.text
            return result_string
    

    else:
        model_id = LLMConfig.MODEL_ID
        #print("Model id:", model_id)
        completion = await client.chat.completions.create(
            model = model_id,
            messages = messages,
            temperature = LLMConfig.TEMPERATURE,
            max_tokens = LLMConfig.MAXTOKENS,
            stream = False
            )
        result_string = completion.choices[0].message.content
        return result_string

async def video_analyzer(images_data: list, previous_events: str = "") -> str:
    """Handle the service call to analyze a video (future implementation)"""

    prompt = LLMConfig.PROMPT.format(previous_events = previous_events)
    # print(prompt)

    content = [{"type": "text", "text": prompt}]
    for each in images_data:
        content.append({
            "type": "image_url",
            "image_url": {"url": each}
            })

    messages = [{"role": "user","content": content}]    
    result_string = await call_api(messages)
    return result_string

def convert_to_json(json_string: str) -> dict:    
    json_str = json_string.strip().strip('```json').strip('```').strip()
    data = json.loads(json_str)    
    return data
