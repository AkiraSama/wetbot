#!/usr/bin/env python3.6

import logging
import sys

import discord

from .bot import Wetbot
from .config import get_configuration

def main(argv=None):
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter(
        fmt='{asctime} {name} [{levelname}] {message}',
        datefmt='%m-%d %H:%M:%S',
        style='{')
    ch.setFormatter(formatter)
    log = logging.getLogger('')
    log.setLevel(logging.DEBUG)
    log.addHandler(ch)
    log.info("logging initialized")

    config = get_configuration(argv[1:], ch)
    token = config.get('bot', 'token')
    if not token:
        log.info("please add your bot token to your configuration " \
                     "file or pass it via the command line")
        return 0
    bot = Wetbot(config)
    bot.run(token)

if __name__ == '__main__':
    main(sys.argv)

