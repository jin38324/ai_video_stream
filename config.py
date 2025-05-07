from typing import Dict, Any
import logging
import os
from dotenv import load_dotenv

load_dotenv()

IP = os.getenv('IP')


# 视频处理配置
class VideoConfig:
    FRAME_INTERVAL = 10  # 分析间隔(秒)
    SCALE = 0.25 # 缩略图缩放比例
    SIMILARITY_THRESHOLD = 0.8 # 相似度阈值，数值越小抽取的帧越少


# API配置
class LLMConfig:
    # 通义千问API配置
    BASE_URL = f"http://{IP}:8000/v1"
    API_KEY = "ocigenerativeai"
    MODEL_ID = "Qwen/Qwen2.5-VL-3B-Instruct" 

    # API请求配置    
    TEMPERATURE = 0.5 # 温度
    MAXTOKENS = 1024 # 最大token数

    PROMPT = """You are an advanced image analysis assistant specializing in extracting precise data from video and images captured by a home security camera.
Your task is to analyze video or images and summary the key events as detail as possible. 
Focus on identifying and describing the actions of people, pet and dynamic objects (e.g., vehicles) rather than static background details. 
Track and summarize movements or changes over time (e.g., 'A person walks to the front door' or 'A car pulls out of the driveway'). 

Provide only json output, with no additional text or commentary. 

Context about previous events:
{previous_events}

Output json as below:
- `description`:string, summary of the event in short Chinese sentence.
- `event_category`: string, 事件类型，包括 火灾,异常停留,⼊侵检测,⼈员跌倒,包裹投递,⽆事件,其它.
- `trigger_alarm`: float, a value between 0 and 1, indicating whether an abnormal situation that requires notification has occurred, with 1 indicating the most serious abnormality.
- `is_new_event`: 1 or 0, a boolean value indicating whether the event is a new event compared to the previous event.
"""

class SummaryLLMConfig:
    # 通义千问API配置
    BASE_URL = f"http://{IP}:8000/v1"
    API_KEY = "ocigenerativeai"
    MODEL_ID = "Qwen/Qwen2.5-VL-3B-Instruct" 

    # API请求配置    
    TEMPERATURE = 0.5 # 温度
    MAXTOKENS = 1024 # 最大token数
    PROMPT =  """You are an advanced image analysis assistant specializing in extracting precise data from video and images captured by a home security camera.
Your task is to summary the key events from a series of events description in context as detail as possible.

Context events description:
{events_context}

Provide only json output, with no additional text or commentary.
Output json as below:
- `title`: string, summary of the event in short Chinese sentence.
- `event_summary`: string, summary of the event in longer Chinese sentence.
"""

class SummaryConfig:
    MAX_GAP_LENGTH = 1*60*1000  # 1分钟内没有相同事件，就开始总结    
    MAX_TIME_LENGTH = 2*60*1000 # 事件长度超过10分钟，不管后面是不是同一事件，就开始总结

# 服务器配置
class ServerConfig:
    HOST = "127.0.0.1"
    PORT = 16532
    RELOAD = False
    WORKERS = 1

# 日志配置
LOG_CONFIG = {
    'level': logging.INFO,
    'format': '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    'handlers': [
        {'type': 'file', 'filename': 'code.log'},
        {'type': 'stream'}
    ]
}

