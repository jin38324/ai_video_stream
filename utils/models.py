from pydantic import BaseModel, Field
from typing import Optional,Literal, Union
import datetime


class VideoInfo(BaseModel):
    # metadata
    device_id: str
    timestamp: int

    # location
    region: str
    namespace: str
    bucket: str
    par: str
    object_name: str

    # video information
    fps: float = 30.0
    width: int = 1280
    height: int = 720

class LLMOutput(BaseModel):
    description: str
    event_catagory: str  # 异常停留 ⼊侵检测 ⼈员跌倒 包裹投递 ⽆事件 其它
    triger_alarm: float = 0   # a value between 0 and 1
    # is_new_event: bool = False # 是否和上一帧是同一事件

class FrameInfo(BaseModel):
    # metadata
    device_id: str
    timestamp: int
    object_name: str
    ssim: float

    thumbnail: Optional[str] = None

    # llm output
    llm_output: Optional[LLMOutput] = None

class EventTag(BaseModel):
    event_catagory: str
    min_time: int = 0
    max_time: int = 0

    def update_max_time(self,max_time:int):
        self.max_time = max_time
    
    def update_min_time(self,min_time:int):
        self.min_time = min_time


class MessagePayload(BaseModel):
    type: Literal['event','summary','alarm']
    device_id : str
    timestamp: int
    thumbnail: str
    description: str
    event_catagory: str
    triger_alarm: float
    

def timestamp_to_str(timestamp:int,style="full"):
    timestamp = timestamp / 1000
    if style=="full":
        timestamp_str = datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S.%f")
    elif style=="simple":
        timestamp_str = datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    return timestamp_str