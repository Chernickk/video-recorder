import redis

redis_client = redis.Redis(host='localhost',
                           db=0,
                           decode_responses=True)
