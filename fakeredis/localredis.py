import json
import os

class LocalRedis:
    """
    A minimal file-backed key-value store.
    Supports basic operations: SET, GET, DELETE.
    Data is persisted as JSON to a local file.
    """

    def __init__(self, filename='local_redis.json'):
        current_path = os.path.dirname(os.path.abspath(__file__))
        self.filename = os.path.join(current_path, filename)
        # Initialize storage file if missing
        if not os.path.exists(self.filename):
            with open(self.filename, 'w',encoding='utf-8-sig') as f:
                json.dump({}, f)

    def _load(self):
        """Load the entire store from disk."""
        with open(self.filename, 'r',encoding='utf-8-sig') as f:
            return json.load(f)

    def _save(self, data):
        """Persist the entire store to disk."""
        with open(self.filename, 'w',encoding='utf-8-sig') as f:
            json.dump(data, f)

    def set(self, key, value):
        """Set the string value of a key."""
        data = self._load()
        data[key] = value
        self._save(data)
        return True

    def get(self, key):
        """Get the value of a key. Returns None if not found."""
        data = self._load()
        return data.get(key)

    def delete(self, key):
        """Delete a key. Returns True if deleted, False if key did not exist."""
        data = self._load()
        if key in data:
            del data[key]
            self._save(data)
            return True
        return False

# 示例用法
# if __name__ == '__main__':
#     store = LocalRedis()
#     store.set('foo', 'bar')
#     print(store.get('foo'))   # 输出: bar
#     store.delete('foo')
#     print(store.get('foo'))   # 输出: None
