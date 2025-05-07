import os
import json
import base64
import time
import uuid
from types import SimpleNamespace # Useful for creating simple objects that mimic SDK responses

# Define placeholder classes to mimic OCI models for clarity
# In a real scenario, you might not need these if you only access .key and .value
class PutMessagesDetailsEntry:
    def __init__(self, key, value):
        # OCI expects value to be base64 encoded bytes, let's enforce that for simulation
        if isinstance(value, str):
            value = value.encode('utf-8')
        self.key = base64.b64encode(key.encode('utf-8')).decode('utf-8') if key else None
        self.value = base64.b64encode(value).decode('utf-8')

class PutMessagesDetails:
    def __init__(self, messages):
        # messages should be a list of PutMessagesDetailsEntry instances
        self.messages = messages

# Simulated Message class similar to oci.streaming.models.Message
class SimulatedMessage:
    def __init__(self, stream, partition, offset, key, value, timestamp):
        self.stream = stream
        self.partition = partition # Simulation uses a single "partition" per file
        self.offset = offset     # Use byte offset in the file as the message offset
        self.key = key           # Store as base64 string (as received from Put)
        self.value = value         # Store as base64 string (as received from Put)
        self.timestamp = timestamp # Store Unix timestamp

class LocalStreamClientSimulator:
    """
    Simulates oci.streaming.StreamClient using local files.
    Stores each stream_id as a '.stream' file in the base_storage_path.
    Messages are stored as JSON lines.
    """
    def __init__(self, base_storage_path="local_oci_streams"):
        """
        Initializes the simulator.

        Args:
            base_storage_path (str): Directory to store stream files.
                                     Defaults to 'local_oci_streams'.
        """
        current_path = os.path.dirname(os.path.abspath(__file__))
        self.base_storage_path = os.path.join(current_path, base_storage_path)
        os.makedirs(self.base_storage_path, exist_ok=True)
        print(f"LocalStreamClientSimulator initialized. Storage path: {self.base_storage_path}")

    def _get_stream_file_path(self, stream_id):
        """Gets the file path for a given stream_id."""
        # Basic sanitization to prevent directory traversal, replace invalid chars
        safe_filename = "".join(c if c.isalnum() or c in ('-', '_', '.') else '_' for c in stream_id)
        if not safe_filename:
            raise ValueError("Invalid stream_id resulting in empty filename")
        return os.path.join(self.base_storage_path, f"{safe_filename}.stream")

    def put_messages(self, stream_id, put_messages_details, **kwargs):
        """
        Simulates putting messages to a stream (appends to a file).

        Args:
            stream_id (str): The identifier of the stream.
            put_messages_details (PutMessagesDetails): Object containing messages to put.
                                                      Expects messages with base64 encoded values.
            **kwargs: Accepts other arguments like opc_request_id for compatibility, but ignores them.

        Returns:
            SimpleNamespace: Mimics the OCI SDK response structure with a 'data' attribute.
                             'data' indicates the number of successful puts (no failure simulation yet).
        """
        file_path = self._get_stream_file_path(stream_id)
        count = 0
        entries_info = [] # To mimic the structure if needed later

        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                current_timestamp = time.time() # Use current time for timestamp
                for msg_entry in put_messages_details.messages:
                    # OCI SDK expects value to be base64 encoded string already
                    # OCI SDK expects key to be base64 encoded string already
                    message_data = {
                        "key": msg_entry.key, # Assumed already base64 encoded string or None
                        "value": msg_entry.value, # Assumed already base64 encoded string
                        "timestamp": current_timestamp,
                        # Add other metadata if needed for simulation
                    }
                    # Append as a JSON line
                    f.write(json.dumps(message_data) + '\n')
                    count += 1
                    # Mimic entry result structure (simplified)
                    entries_info.append(SimpleNamespace(error=None, error_message=None, offset=None, partition=None)) # Offset/Partition not known until read in real OCI

            # Simulate the response structure
            # Real response has 'failures' (int) and 'entries' (list) in data
            response_data = SimpleNamespace(failures=0, entries=entries_info) # Simple success simulation
            response = SimpleNamespace(data=response_data, status=200, headers={})
            print(f"Simulated put_messages to '{stream_id}': {count} messages.")
            return response

        except Exception as e:
            print(f"Error in simulated put_messages for '{stream_id}': {e}")
            # Simulate an error response (basic)
            response_data = SimpleNamespace(failures=len(put_messages_details.messages), entries=[])
            response = SimpleNamespace(data=response_data, status=500, headers={}, error=str(e))
            return response

    def get_messages(self, stream_id, cursor, limit=10, **kwargs):
        """
        Simulates getting messages from a stream (reads from a file).

        Args:
            stream_id (str): The identifier of the stream.
            cursor (str): The position from where to start reading.
                          In this simulation, it's the byte offset in the file.
                          Use '0' for the beginning.
            limit (int): Maximum number of messages to retrieve. Defaults to 10.
            **kwargs: Accepts other arguments like opc_request_id for compatibility, but ignores them.


        Returns:
            SimpleNamespace: Mimics the OCI SDK response structure.
                             'data' contains a list of SimulatedMessage objects.
                             'headers' contains 'opc-next-cursor'.
        """
        file_path = self._get_stream_file_path(stream_id)
        messages = []
        next_cursor = cursor # Default to same cursor if no messages read

        try:
            if not os.path.exists(file_path):
                # Return empty response if stream file doesn't exist
                response = SimpleNamespace(data=[], status=200, headers={'opc-next-cursor': cursor})
                print(f"Simulated get_messages from '{stream_id}': Stream file not found.")
                return response

            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    # The cursor is the byte offset
                    start_offset = int(cursor)
                    f.seek(start_offset)
                except (ValueError, TypeError):
                    print(f"Warning: Invalid cursor '{cursor}'. Starting from beginning (offset 0).")
                    start_offset = 0
                    f.seek(0)

                current_offset = f.tell() # Offset before reading the first line
                line_count = 0
                while line_count < limit:
                    line = f.readline()
                    if not line:
                        # End of file reached
                        next_cursor = str(f.tell()) # Cursor points to EOF
                        break

                    line = line.strip()
                    if not line: # Skip empty lines if any
                        current_offset = f.tell()
                        continue

                    try:
                        message_data = json.loads(line)
                        # Create a simulated message object
                        msg = SimulatedMessage(
                            stream=stream_id,
                            partition="0", # Single simulated partition
                            offset=current_offset, # Offset *before* reading this line
                            key=message_data.get("key"), # Already base64 string or None
                            value=message_data.get("value"), # Already base64 string
                            timestamp=message_data.get("timestamp", time.time()) # Use stored or current time
                        )
                        messages.append(msg)
                        line_count += 1
                        current_offset = f.tell() # Update offset for the *next* potential read
                        next_cursor = str(current_offset) # The cursor to use next time is the start of the next line
                    except json.JSONDecodeError as jde:
                        print(f"Warning: Skipping malformed JSON line in '{file_path}' at offset near {current_offset}: {jde}")
                        current_offset = f.tell() # Advance past the bad line
                        next_cursor = str(current_offset)
                    except Exception as ex:
                         print(f"Warning: Error processing line in '{file_path}' at offset near {current_offset}: {ex}")
                         current_offset = f.tell() # Advance past the bad line
                         next_cursor = str(current_offset)


            # Simulate the response structure
            # Real response is the list of messages directly in 'data'
            # The next cursor is in the 'opc-next-cursor' header
            response = SimpleNamespace(
                data=messages,
                status=200,
                headers={'opc-next-cursor': next_cursor}
            )
            print(f"Simulated get_messages from '{stream_id}' (Cursor: {cursor}): Read {len(messages)} messages. Next cursor: {next_cursor}")
            return response

        except FileNotFoundError:
             response = SimpleNamespace(data=[], status=200, headers={'opc-next-cursor': cursor})
             print(f"Simulated get_messages from '{stream_id}': Stream file not found.")
             return response
        except Exception as e:
            print(f"Error in simulated get_messages for '{stream_id}': {e}")
            # Simulate an error response (basic)
            response = SimpleNamespace(data=[], status=500, headers={'opc-next-cursor': cursor}, error=str(e))
            return response



