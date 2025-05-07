
import asyncio

from summary import EventProcessor
import time

while True:    
    print("="*12,"Summary Running...","="*12)
    event_processor = EventProcessor(device_id="device_123456")
    event_processor.process_event()
    time.sleep(10)