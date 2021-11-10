import redis

redis_client = redis.Redis(
    host='localhost',
    db=0,
    decode_responses=True
)

redis_client_pickle = redis.Redis(
    host='localhost',
    db=0,
    decode_responses=False
)
