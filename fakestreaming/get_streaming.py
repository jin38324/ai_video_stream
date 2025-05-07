
from .streaming import LocalStreamClientSimulator, PutMessagesDetails, PutMessagesDetailsEntry
import json
import base64
import time


print("\n--- Getting Messages ---")


def get_messages(cursor, limit=2, **kwargs):
    simulator = LocalStreamClientSimulator(base_storage_path="my_local_streams")
    my_stream_id = "ocid1.stream.oc1..exampleuniqueID"
    data = True
    while data:
        time.sleep(1)
        get_response = simulator.get_messages(stream_id=my_stream_id, cursor=cursor, limit=limit)
        data = get_response.data
        #print(f"\nGet 1 Status: {get_response.status}")
        #print(f"Get 1 Next Cursor: {get_response.headers.get('opc-next-cursor')}")
        cursor = get_response.headers.get('opc-next-cursor')
    
        for msg in get_response.data:
            # Decode key/value for display if needed (remember they are base64)
            key_decoded = base64.b64decode(msg.key).decode('utf-8') if msg.key else None
            try:
                value_decoded = base64.b64decode(msg.value).decode('utf-8')
            except UnicodeDecodeError:
                value_decoded = base64.b64decode(msg.value) # Keep as bytes if not utf-8
            # print(f"  Offset: {msg.offset}, Key: {key_decoded}, Value: {value_decoded}, Timestamp: {msg.timestamp}")

            yield value_decoded

if __name__ == "__main__":
    for msg in get_messages(cursor="100", limit=2):
        print(msg)