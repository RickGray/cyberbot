def run(seed):
    """ function to run

    Args:
        seed: The value of each line striped in seed file

    Returns:
        String, object, list, directory, etc.
    """

    name, age = seed.split(',')
    return 'Hello World! {}, {}'.format(seed, int(age))


def callback(result):
    """ callback function to call
    
    Args:
        result: ProcessTask instance pool_task_with_timeout() method returned

        result = {
            'seed': 'Jone',
            'data': 'Hello World! Jone',
            'exception': None
        }

        or 

        result = {
            'seed': 'Jone',
            'data': None,
            'exception': 'ValueError: invalid literal'
        }

    Returns:
        Anything want to return.
    """

    seed = result['seed']
    data = result['data']
    exception = result['exception']

    print('seed: "{}", data: "{}", exception: "{}"'
          .format(seed, data, exception))
