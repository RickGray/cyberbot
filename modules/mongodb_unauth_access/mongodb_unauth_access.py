import gevent
import pymongo

gevent.monkey.patch_all()


def run(seed):
    try:
        ip, port = seed.split(':')
    except ValueError as ex:
        ip, port = seed, 27017

    conn = pymongo.MongoClient(ip, int(port), connectTimeoutMS=2000,
                               serverSelectionTimeoutMS=2000,
                               maxPoolSize=1000, waitQueueMultiple=1000,
                               connect=False)
    if conn.database_names():
        info = conn.server_info()
    return info


def callback(result):
    seed = result['seed']
    data = result['data']
    exception = result['exception']

    if data:
        version = data.get('version', '') if data else None

        print('seed: "{}", version: "{}", exception: "{}"'
              .format(seed, version, exception))



if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Usage: python {} <seed>'.format(sys.argv[0]))
        sys.exit()

    callback(dict(seed=sys.argv[1].strip(),
                  data=run(sys.argv[1].strip()),
                  exception=None))
