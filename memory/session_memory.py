import redis
import json

# connect to redis server
redis_client = redis.Redis(host="localhost", port=6379, db=0)


def store_session(session_id: str, data: dict):
    key = f"session:{session_id}"

    redis_client.set(key, json.dumps(data))

    return True


def get_session(session_id: str):
    key = f"session:{session_id}"

    data = redis_client.get(key)

    if data:
        return json.loads(data)

    return {}