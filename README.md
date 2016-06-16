# cyberbot

Cyberbot is a lightweight batch scanning framework based on gevent. Security researchers wrote many sample PoCs for vulnerabilities, using cyberbot framework to do batch scanning easily.

Install
----

Cyberbot framework based on [gevent](http://www.gevent.org) library, you must install gevent library for the first:

    pip install gevent

Then clone this repository:

    git clone https://github.com/RickGray/cyberbot.git cyberbot

Cyberbot framework works out of the box with [Python](http://www.python.org/download/) version **2.7.x** and [gevent](http://www.gevent.org) support.

Usage
----

Start with a JSON configuration file loaded:

    python cyberbot.py -c modules/helloworld/config.json

Or override options with commands:

    python cyberbot.py -n helloworld \
                       -r modules/helloworld/helloworld.py \
                       -t modules/helloworld/peoples.txt \
                       --poc-func=run \
                       --poc-callback=callback \
                       --task-dir=tasks/test_helloworld \
                       --proc-num=4 \
                       --pool-size=20 \
                       --pool-timeout=120

To get a list of all options use:

    python cyberbot.py -h

Also can run console monitor with `--enable-console` option:

![](screenshots/console_monitor.gif)
