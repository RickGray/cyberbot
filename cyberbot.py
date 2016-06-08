#!/usr/bin/env python
# coding: utf-8

import os
import sys
import json
import math
import time
import shutil

from argparse import ArgumentParser
from itertools import chain
from itertools import islice
from multiprocessing import Process

from gevent import pool
from gevent import monkey
from gevent import timeout

monkey.patch_socket()


class OptException(Exception):
    pass


def count_file_linenum(filename):
    """ Count the number of lines in file

    Args:
        filename: A file path need to count the number of lines

    Returns:
        A Integer, the number of lines in file.
    """
    with open(filename) as f:
        n = f.readlines().__len__()
    return n


def split_file_by_linenum(filename, linenum_of_perfile=30*10**6):
    """ Split one file into serval files with a solit line number

    Args:
        filename: A file path need to split with linenum
        linenum_of_perfile: The line number of per file

    Returns:
        Filenames list has already splited.
    """
    def chunks(iterable, n):
        iterable = iter(iterable)
        while True:
            yield chain([next(iterable)], islice(iterable, n-1))

    filenames = []
    with open(filename) as f:
        for i, lines in enumerate(chunks(f, linenum_of_perfile)):
            _ = '{}_{:02d}'.format(filename, i)
            filenames.append(_)
            with open(_, 'w') as wf:
                wf.writelines(lines)
    return filenames


def split_file_by_filenum(filename, filenum):
    """ Split one file into serval files with a number of files """
    if filenum <= 1:
        filenames = [filename]
    else:
        linenum = count_file_linenum(filename)
        if linenum < filenum:
            raise OptException('proc_num more than line number of seed file')
        linenum_of_perfile = int(math.ceil(linenum / float(filenum)))
        filenames = split_file_by_linenum(filename, linenum_of_perfile)
    return filenames


class Config(object):
    scanname = None  # scanning task name
    seedfile = None  # seed file path to process
    task_dir = None  # task files stored directory
    proc_num = None  # process number to use
    pool_size = None  # pool task size of per process
    pool_timeout = None  # pool task timeout of per process
    poc_file = None  # poc file path
    poc_func = None  # function to run in poc file
    poc_callback = None  # callback function in poc file

    scan_func = None  # function method instance
    scan_callback = None  # callback method instance

    def from_keys(self, keys):
        for k, v in keys.items():
            if hasattr(self, k) and v is not None:
                setattr(self, k, v)

    def from_jsonfile(self, jsonfile):
        """ Load options from json file """
        with open(jsonfile) as f:
            content = f.read()
        keys = json.loads(content)
        self.from_keys(keys)

    @property
    def __dict__(self):
        return dict(scanname=self.scanname,
                    seedfile=self.seedfile,
                    task_dir=self.task_dir,
                    proc_num=self.proc_num,
                    pool_size=self.pool_size,
                    pool_timeout=self.pool_timeout,
                    poc_file=self.poc_file,
                    poc_func=self.poc_func,
                    poc_callback=self.poc_callback)


class ProcessTask(object):
    def __init__(self, scan_func, pool_size, pool_timeout):
        self.scan_func = scan_func
        self.pool_size = pool_size
        self.pool_timeout = pool_timeout

    @staticmethod
    def callback(result):
        return result

    def pool_task_with_timeout(self, line):
        seed = line.strip()
        result = dict(seed=seed, data=None, exception=None)
        try:
            data = timeout.with_timeout(self.pool_timeout,
                                        self.scan_func,
                                        seed)
        except (Exception, timeout.Timeout) as ex:
            result['exception'] = str(ex)
        else:
            result['data'] = data
        return result

    def run(self, seedfile):
        po = pool.Pool(self.pool_size)
        with open(seedfile) as f:
            for line in f:
                po.add(po.apply_async(func=self.pool_task_with_timeout,
                                      args=(line, ),
                                      kwds=None,
                                      callback=self.callback))

        try:
            po.join()
        except (KeyboardInterrupt, SystemExit) as ex:
            print(str(ex))
            po.kill()


class Launcher(object):
    def __init__(self, options):
        self.config = Config()
        self.init_conf(options)
        self.init_env()
        self.init_mod()

    def init_conf(self, options):
        if options.CONFIG:
            self.config.from_jsonfile(options.CONFIG)
        opts = vars(options)
        opts.pop('CONFIG')
        opts = dict((k.lower(), v) for k, v in opts.items())
        self.config.from_keys(opts)

        # check options required
        for k, v in opts.items():
            if hasattr(self.config, k):
                value = getattr(self.config, k)
                if value is None:
                    raise OptException('{} option required, '
                                       'use -h for help'.format(k))

    def init_env(self):
        cwd = os.getcwd()
        task_dir = os.path.realpath(os.path.join(cwd, self.config.task_dir))
        seedfile = os.path.realpath(os.path.join(cwd, self.config.seedfile))
        poc_file = os.path.realpath(os.path.join(cwd, self.config.poc_file))

        try:
            self.config.proc_num = int(self.config.proc_num)
            self.config.pool_size = int(self.config.pool_size)
            self.config.pool_timeout = int(self.config.pool_timeout)
        except ValueError as ex:
            raise OptException('wrong option type, "{}"'.format(str(ex)))

        if not os.path.exists(seedfile):
            raise OptException('seed file not exists, {}'.format(seedfile))
        if not os.path.exists(poc_file):
            raise OptException('poc file not exists, {}'.format(poc_file))

        if not os.path.exists(task_dir):
            os.makedirs(task_dir)

        timestamp = time.strftime('%Y%m%d-%H%M%S', time.localtime())
        task_runtime_dir = os.path.join(task_dir, timestamp)
        if not os.path.exists(task_runtime_dir):
            os.makedirs(task_runtime_dir)

        shutil.copy(seedfile, task_runtime_dir)
        self.config.seedfile = os.path.realpath(os.path.join(task_runtime_dir,
                                                os.path.basename(seedfile)))
        shutil.copy(poc_file, task_runtime_dir)
        self.config.poc_file = os.path.realpath(os.path.join(task_runtime_dir,
                                                os.path.basename(poc_file)))
        self.config.task_dir = task_dir

        # dump options to json file in task directory
        d_opts = vars(self.config)
        conffile = os.path.join(task_runtime_dir, 'config.json')
        with open(conffile, 'w') as f:
            f.write(json.dumps(d_opts, indent=4, sort_keys=True))

        os.chdir(task_runtime_dir)

    def init_mod(self):
        sys.path.append(
            os.path.abspath(os.path.dirname(self.config.poc_file)))
        poc_name = os.path.splitext(os.path.basename(self.config.poc_file))[0]
        poc_mod = __import__(poc_name)
        self.config.scan_func = getattr(poc_mod, self.config.poc_func)
        if self.config.poc_callback:
            self.config.scan_callback = getattr(poc_mod,
                                                self.config.poc_callback)

    def run(self):
        """ Start ProcessTask main function """
        filenames = split_file_by_filenum(self.config.seedfile,
                                          self.config.proc_num)
        processes = []
        w = ProcessTask(self.config.scan_func,
                        self.config.pool_size,
                        self.config.pool_timeout)
        if self.config.scan_callback:
            w.callback = self.config.scan_callback

        for i, filename in enumerate(filenames):
            proc_name = 'launcher_{}_{:02d}'.format(self.config.scanname, i)
            p = Process(name=proc_name,
                        target=w.run,
                        args=(filename, ))
            if p not in processes:
                processes.append(p)

        for p in processes:
            p.start()
        for p in processes:
            p.join()


BANNER = '''
____________       ______             ______       _____
_____  ____/____  ____  /________________  /_________  /_
____  /    __  / / /_  __ \  _ \_  ___/_  __ \  __ \  __/
   / /___  _  /_/ /_  /_/ /  __/  /   _  /_/ / /_/ / /_
   \____/  _\__, / /_.___/\___//_/    /_.___/\____/\__/
           /____/

'''

DESC = 'A lightweight batch scanning framework based on gevent.'


def commands():
    parser = ArgumentParser(description=DESC)

    parser.add_argument('-c', '--config', dest='CONFIG', default=None,
                        type=str, help='config file of launcher')
    parser.add_argument('-n', '--scanname', dest='SCANNAME',
                        type=str, help='alias name of launcher')
    parser.add_argument('-t', '--seedfile', dest='SEEDFILE',
                        type=str, help='seed file path to scan')
    parser.add_argument('-r', '--poc-file', dest='POC_FILE',
                        type=str, help='poc file path to load')
    parser.add_argument('-f', '--poc-func', dest='POC_FUNC',
                        type=str, help='function name to run in poc file')
    parser.add_argument('-b', '--poc-callback', dest='POC_CALLBACK',
                        type=str, help='callback function name in poc file')

    parser.add_argument('--task-dir', dest='TASK_DIR',
                        help='task files stored directory')
    parser.add_argument('--proc-num', dest='PROC_NUM',
                        type=int, help='process numbers to run')
    parser.add_argument('--pool-size', dest='POOL_SIZE',
                        type=int, help='pool size in per process')
    parser.add_argument('--pool-timeout', dest='POOL_TIMEOUT',
                        type=int, help='pool timeout in per process')

    return parser.parse_args()


if __name__ == '__main__':
    print BANNER
    args = commands()
    launcher = Launcher(args)
    launcher.run()
