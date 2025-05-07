from video_server import VideoProcessor
from utils.models import VideoInfo
from fakestreaming.get_streaming import get_messages
import json
import multiprocessing
import asyncio


for msg in get_messages(cursor="100", limit=2):
    data = json.loads(json.loads(msg))
    print(data)
    video_info = VideoInfo(**data)

    processor = VideoProcessor(video_info)
    asyncio.run(processor.extract_frames())
    #asyncio.run(VideoProcessor(video_info).extract_frames())
    # # 创建并启动后台线程
    # process  = multiprocessing.Process(target=processor.extract_frames)
    # process.start()