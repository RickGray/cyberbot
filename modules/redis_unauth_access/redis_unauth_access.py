import redis


def run(seed):
    try:
        ip, port = seed.split(':')
    except ValueError as ex:
        ip, port = seed, 6379

    r = redis.Redis(ip, int(port), socket_connect_timeout=5)
    info = r.info()
    return info


def callback(result):
    seed = result['seed']
    data = result['data']
    exception = result['exception']

    if data:
        version = data.get('redis_version', '') if data else None
        os = data.get('os', '') if data else None

        print('seed: "{}", version: "{}", os: "{}", exception: "{}"'
              .format(seed, version, os, exception))


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Usage: python {} <seed>'.format(sys.argv[0]))
        sys.exit()

    callback(dict(seed=sys.argv[1].strip(),
                  data=run(sys.argv[1].strip()),
                  exception=None))
