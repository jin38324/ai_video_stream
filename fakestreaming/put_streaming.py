import os
import sys

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)

from streaming import LocalStreamClientSimulator, PutMessagesDetails, PutMessagesDetailsEntry
import json
from utils.models import VideoInfo
import time

# --- Example Usage ---

# 1. Initialize the Simulator
simulator = LocalStreamClientSimulator(base_storage_path="my_local_streams")

# 2. Define a Stream ID
my_stream_id = "ocid1.stream.oc1..exampleuniqueID"

# 清空文件
file = simulator._get_stream_file_path(my_stream_id)
with open(file, 'w', encoding='utf-8') as f:
    f.write("")

allcount = 80
for i in range(allcount):
    object_name = f"hualai/7_家中火灾/7_家中火灾_segment_{str(i).zfill(4)}.mp4"
    print(object_name)

    videoinfo = VideoInfo(
        device_id = "device_123456",
        timestamp = int(time.time() * 1000),
        region = "us-ashburn-1",
        namespace = "sehubjapacprod",
        bucket = "bucket-media-input",
        par = "KC8WSQz49_flQrzxTZglbWSPkbOuYXORNIXo8LBV52CMyXmILN46VfMBtJs6kXb_",
        object_name = object_name
        )
    data = videoinfo.model_dump_json()
    json_data = json.dumps(data)
    print(json_data)
    # 3. Put some messages

    put_details = PutMessagesDetails(
        messages=[ 
            PutMessagesDetailsEntry(key="message-key-1", value=json_data) 
            ])

    put_response = simulator.put_messages(stream_id=my_stream_id, put_messages_details=put_details)
    print("Put response status:", put_response.status)
    time.sleep(5)
