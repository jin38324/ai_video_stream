import cv2 
import asyncio 
import json
from datetime import datetime 
from concurrent.futures import ThreadPoolExecutor 

from collections import deque 
from typing import Optional, Dict, Any , List,Set
import numpy as np 
import logging 
# from multi_modal_analyzer import MultiModalAnalyzer
import time
import uvicorn 
import requests
from multiprocessing import set_start_method 
from config import VideoConfig, ServerConfig, LOG_CONFIG


from utils import media, llm
from utils.models import (
    VideoInfo, 
    LLMOutput, 
    FrameInfo,
    EventTag,
    #timestamp_to_str,
    MessagePayload
    )

from fakeredis.localredis import LocalRedis

kv_store = LocalRedis()



# 配置日志记录
logging.basicConfig(
    level=LOG_CONFIG['level'],
    format=LOG_CONFIG['format'],
    handlers=[logging.FileHandler(LOG_CONFIG['handlers'][0]['filename'], encoding='utf-8'), logging.StreamHandler()]
)





# 视频流处理器 
class VideoProcessor:
    def __init__(self, video_info):
        self.video_info = video_info
        self.device_id = video_info.device_id
        self.timestamp = video_info.timestamp

        self.video_source = self.get_url()
        self.cap = self.open_video()

        self.get_video_info()
        # self.frame_buffer = deque(maxlen=3)
        # self.message_buffer = deque(maxlen=3)

        self.prev_frame = None
        self.data_processor = DataProcessor()

    def get_url(self):
        domian = f"https://objectstorage.{self.video_info.region}.oraclecloud.com"
        par = f"p/{self.video_info.par}"
        namespace = f"n/{self.video_info.namespace}"
        bucket = f"b/{self.video_info.bucket}"
        object_name = f"o/{self.video_info.object_name}"
        url = f"{domian}/{par}/{namespace}/{bucket}/{object_name}"
        return url
    
    def open_video(self):
        cap = cv2.VideoCapture(self.video_source)
        if not cap.isOpened():
            logging.error(f"Failed to open {self.video_source}, trying with CAP_FFMPEG backend...")
            cap = cv2.VideoCapture(self.video_source, cv2.CAP_FFMPEG)
            if not cap.isOpened():
                logging.error(f"Error: Could not open video file {self.video_source}")
        return cap


    def get_video_info(self):
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            logging.warning(f"Warning: Could not determine frame count for {self.video_source}")
            total_frames = float('inf')
        self.total_frames = total_frames

        # 获取视频宽度和高度
        self.width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)


    async def extract_frames(self):
        """Extract frames from video with device ID and timestamp in frame names"""
        frame_count = 0
        keyframe_count = 0
        is_keyframe = True
        while self.cap.isOpened():
            #try:
            ret, frame = self.cap.read()
            if not ret:
                break

            # Only save frames at specified intervals
            if frame_count % VideoConfig.FRAME_INTERVAL == 0:
                # Calculate timestamp for current frame (in milliseconds)
                frame_time_ms = int((frame_count / self.fps) * 1000)
                frame_timestamp = self.timestamp + frame_time_ms
                
                # 转换颜色空间并缓冲 
                if frame.dtype != np.uint8:
                    frame = frame.astype(np.uint8)
                if len(frame.shape) == 2:
                    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

                if self.prev_frame is None:
                    is_keyframe = True
                    ssim = 0
                else:
                    ssim = media._similarity_score(self.prev_frame, frame)
                    # print("ssim:", ssim)
                    if ssim < VideoConfig.SIMILARITY_THRESHOLD:
                        is_keyframe = True
                    else:
                        is_keyframe = False

                if is_keyframe:
                    frame_info = FrameInfo(
                        device_id = self.video_info.device_id, 
                        timestamp = frame_timestamp,
                        object_name = self.video_info.object_name,
                        ssim = ssim
                        )

                    # self.process_keyframe(frame,frame_info)
                    # asyncio.run(self.process_keyframe(frame,frame_info))
                    await self.process_keyframe(frame,frame_info)

                    self.prev_frame = frame
                    keyframe_count += 1
            
            frame_count += 1                
            # except Exception as e:
            #     logging.error(f"Error processing frame {frame_count} from {self.video_info.object_name}: {str(e)}")
            #     break

        self.cap.release()
        logging.info(f"Extracted {keyframe_count} / {self.total_frames} frames from {self.video_info.object_name}")

    async def process_keyframe(self,frame,frame_info):
        thumbnail = media.ndarray_to_base64(image_np = frame, 
                                            scale=VideoConfig.SCALE)
        frame_info.thumbnail = thumbnail
        string_result = await self.llm_analysis(frame,frame_info)
        #try:
        json_result = llm.convert_to_json(string_result)
        llm_output = LLMOutput(
            description=json_result["description"],
            event_catagory=json_result["event_category"],
            triger_alarm=json_result["trigger_alarm"],
            # is_new_event=json_result["is_new_event"]
            )
        frame_info.llm_output = llm_output
        self.data_processor.save_frameinfo(frame_info)
        # self.message_buffer.append(frame_info)

        # 保存事件类型
        self.save_event_time(frame_info,json_result)

        # 发送消息        
        self.send_message(frame_info)
            

        # except Exception as e:
        #     logging.error(f"Error converting string to JSON: {str(e)}")
        #     print(string_result)
        #     json_result = None


    async def llm_analysis(self,frame,frame_info):
        images_data = [media.ndarray_to_base64(frame)]
        previous_events = ""
        # for each in self.message_buffer:
        #     previous_events += f"""{timestamp_to_str(each.timestamp)}: {each.llm_output.event_catagory} {each.llm_output.description}\n"""
        
        # previous_events += f"\nCurrent time: {timestamp_to_str(frame_info.timestamp)}\n"
        string_result = await llm.video_analyzer(images_data,previous_events)
        print(string_result)
        return string_result
    
    def save_event_time(self,frame_info,json_result):
        device_data = kv_store.get(frame_info.device_id)
        if device_data is None:
            device_data = {
                json_result["event_category"]:
                {
                    "min_time" : frame_info.timestamp,
                    "max_time" : frame_info.timestamp
                    }
            }
        else:
            if json_result["event_category"] in device_data:
                device_data[json_result["event_category"]]["max_time"] = frame_info.timestamp
            else:
                device_data[json_result["event_category"]] = {
                    "min_time" : frame_info.timestamp,
                    "max_time" : frame_info.timestamp
                    }
        print(device_data)
        kv_store.set(frame_info.device_id,device_data)

    def send_message(self, frame_info: FrameInfo):
        notify_message = MessagePayload(
            type = "event",
            device_id = frame_info.device_id,
            timestamp = frame_info.timestamp,
            thumbnail = frame_info.thumbnail,
            description = frame_info.llm_output.description,
            event_catagory = frame_info.llm_output.event_catagory,
            triger_alarm = frame_info.llm_output.triger_alarm
        )

        SEND_URL = "http://127.0.0.1:16532/sendjson"
        res = requests.post(SEND_URL, json=notify_message.model_dump())
        return
        

        



import sqlite3

class DataProcessor:
    def __init__(self):
        self.conn = sqlite3.connect('data.db')
        self.cur  = self.conn.cursor()
        self.init_table()

    def init_table(self):
        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS video_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT,
                timestamp INTEGER,
                object_name TEXT,
                ssim REAL,
                thumbnail TEXT,
                description TEXT,
                event_catagory TEXT,
                triger_alarm REAL,
                is_new_event BOOLEAN
            )
        ''')
        self.conn.commit()

    def save_frameinfo(self,frame_info:FrameInfo):
        llm_output = frame_info.llm_output
        self.cur.execute('''
            INSERT INTO video_info (device_id, timestamp, object_name, ssim, thumbnail,
                         description, event_catagory, triger_alarm)
            VALUES (?, ?, ?,?, ?, ?, ?, ?)''', 
        (frame_info.device_id,frame_info.timestamp,frame_info.object_name,frame_info.ssim,frame_info.thumbnail,
         llm_output.description,llm_output.event_catagory,llm_output.triger_alarm)
        )
        self.conn.commit()
        logging.info(f"Saved frame info: {llm_output.description}")


# python video_server.py --video_source "./测试视频/小猫开门.mp4"