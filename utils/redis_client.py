import redis

redis_client = redis.Redis(
    host='127.0.0.1',
    db=0,
    decode_responses=True
)

redis_client_pickle = redis.Redis(
    host='127.0.0.1',
    db=0,
    decode_responses=False
)
