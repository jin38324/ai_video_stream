import logging 
from config import SummaryLLMConfig, SummaryConfig, LOG_CONFIG
import time

import asyncio
from utils import llm_sum

from utils.models import (    
    timestamp_to_str
    )

from fakeredis.localredis import LocalRedis

kv_store = LocalRedis()

# 配置日志记录
logging.basicConfig(
    level=LOG_CONFIG['level'],
    format=LOG_CONFIG['format'],
    handlers=[logging.FileHandler(LOG_CONFIG['handlers'][0]['filename'], encoding='utf-8'), logging.StreamHandler()]
)


class EventProcessor:
    def __init__(self,device_id):
        self.device_id = device_id
        self.data_processor = EventDataProcessor()

    def get_memory_events(self):
        device_data = kv_store.get(self.device_id)
        if device_data is None:
            return None
        else:
            return device_data


    def process_event(self):   
        device_data = self.get_memory_events()
        if device_data:
            current_timestamp = int(time.time() * 1000)
            for k,v in device_data.items():
                run_summary = False
                min_time = v["min_time"]
                max_time = v["max_time"]
                time_length = max_time - min_time
                time_gap = current_timestamp -max_time 

                if max_time <= min_time:
                    run_summary = False
                else:
                    if time_gap >= SummaryConfig.MAX_GAP_LENGTH:
                        run_summary = True
                    if time_length >= SummaryConfig.MAX_TIME_LENGTH:
                        run_summary = True
                print("event_catagory:",k,"min_time:",min_time  ,"max_time:",max_time,"current_timestamp:",current_timestamp)
                print("time_length:",time_length,"time_gap:",time_gap)
                print("run_summary:",run_summary)
                if run_summary:
                    events_data = self.data_processor.get_events(self.device_id,k,min_time,max_time)
                    if events_data is not None:
                        llm_data = asyncio.run(self.llm_summary(events_data))
                        data = self.process_data(current_timestamp,events_data,llm_data)
                        self.data_processor.save_events(data)

                        device_data[k]["min_time"] = max_time
                        device_data[k]["max_time"] = max_time
                        kv_store.set(self.device_id,device_data)
    
    async def llm_summary(self,events_data):
        events_context = ""
        for each in events_data["events"]:
            events_context += f"""{each["timestamp"]}, {each["description"]} \n"""
        prompt = SummaryLLMConfig.PROMPT.format(events_context = events_context)
        print(prompt)
        messages = [{"role": "user","content": prompt}]
        result_string = await llm_sum.call_api(messages)
        # print(result_string)
        llm_data = llm_sum.convert_to_json(result_string)
        print(llm_data)    
        return llm_data
    
    def process_data(self,timestamp,events_data,llm_data):
        data = {
            "device_id":self.device_id,
            "timestamp":timestamp,
            "event_catagory":events_data["event_catagory"],
            "min_timestamp":events_data["min_timestamp"],
            "max_timestamp":events_data["max_timestamp"]
            }
        data["title"] = llm_data["title"]
        data["event_summary"] = llm_data["event_summary"]
        return data

import sqlite3

class EventDataProcessor:
    def __init__(self):
        self.conn = sqlite3.connect('data.db')
        self.cur  = self.conn.cursor()
        self.init_table()

    def init_table(self):
        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS video_event_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT,
                timestamp INTEGER,
                min_timestamp INTEGER,
                max_timestamp INTEGER,
                event_catagory TEXT,
                title TEXT,
                event_summary TEXT,
                thumbnail TEXT
            )''')
        self.conn.commit()

    def get_events(self,device,event_catagory,min_time,max_time):
        self.cur.execute('''
            SELECT timestamp,description
            FROM video_info 
            WHERE device_id = ? and event_catagory = ? and timestamp > ? and timestamp <= ?
            order by timestamp asc
            ''',(device,event_catagory,min_time,max_time)
        )
        rows = self.cur.fetchall()
        if not rows:
            return None
        else:
            data = {"event_catagory":event_catagory,
                    "events":[]}
            for each in rows:
                if "min_timestamp" not in data:
                    data["min_timestamp"] = each[0]
                data["max_timestamp"] = each[0]
                data["events"].append({"timestamp":timestamp_to_str(each[0]),"description":each[1]})
            return data
    
    def get_thumbnail(self,device_id,timestamp):
        self.cur.execute('''
            SELECT thumbnail
            FROM video_info 
            WHERE device_id = ? and timestamp = ?
            ''',(device_id,timestamp)
        )
        rows = self.cur.fetchone()
        if rows:
            return rows[0]
        else:
            return None
    
    def save_events(self,data):
        thumbnail = self.get_thumbnail(data["device_id"],data["min_timestamp"])
        data["thumbnail"] = thumbnail
        self.cur.execute('''
            INSERT INTO video_event_summary (device_id, timestamp, min_timestamp, max_timestamp, thumbnail,
                        title, event_summary, event_catagory)
            VALUES (?, ?, ?, ?, ?, ?, ?,?)''', 
            (data["device_id"],data["timestamp"],data["min_timestamp"],data["max_timestamp"],data["thumbnail"],
             data["title"],data["event_summary"],data["event_catagory"])
            )
        self.conn.commit()
        logging.info(f"Saved event data: {data['title']}")


