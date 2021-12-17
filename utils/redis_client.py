from typing import Union

import redis


class RedisClient:
    def __init__(self, host: str, db: int):
        self.client = redis.Redis(
            host=host,
            db=db,
            decode_responses=True
        )

    def get(self, key: str):
        value = self.client.get(key)
        try:
            return float(value)
        except ValueError:
            return value

    def set(self, key: str, value: Union[int, str, bool]):
        if isinstance(value, bool):
            value = float(value)
        return self.client.set(key, value)

    def len(self, key: str):
        return self.client.llen(key)

    def get_full_list(self, key: str):
        return self.client.lrange(key, 0, -1)

    def get_list_slice(self, key: str, from_int: int, to_int: int):
        return self.client.lrange(key, from_int, to_int)

    def lpop(self, key: str):
        return self.client.lpop(key)

    def rpop(self, key: str):
        return self.client.rpop(key)

    def lpush(self, key: str, value: Union[int, str, bool]):
        return self.client.lpush(key, value)

    def rpush(self, key: str, value: Union[int, str, bool]):
        return self.client.rpush(key, value)


class RedisClientNoDecode(RedisClient):
    def __init__(self, host: str, db: int):
        self.client = redis.Redis(
            host=host,
            db=db,
            decode_responses=False
        )


redis_client = RedisClient(host='redis', db=0)
redis_client_pickle = RedisClientNoDecode(host='redis', db=0)
