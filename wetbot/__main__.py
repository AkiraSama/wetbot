#!/usr/bin/env python3.6

import logging
import sys

from wetbot.bot import Wetbot
from wetbot.config import get_configuration

ANSI_RESET = '\x1b[0m'
ANSI_RED = '\x1b[31m'
ANSI_GREEN = '\x1b[32m'
ANSI_YELLOW = '\x1b[33m'
ANSI_BLUE = '\x1b[34m'
ANSI_MAGENTA = '\x1b[35m'
ANSI_CYAN = '\x1b[36m'

LOGGING_COLORS = (
    (logging.DEBUG, ANSI_CYAN),
    (logging.INFO, ANSI_GREEN),
    (logging.WARN, ANSI_YELLOW),
    (logging.ERROR, ANSI_RED)
)

LOG_FORMAT_STR = '{asctime} {name} [{levelname}] {message}'
LOG_FORMAT_STR_COLOR = (
    f'{ANSI_BLUE}{{asctime}}{ANSI_RESET} '
    f'{ANSI_MAGENTA}{{name}}{ANSI_RESET} '
    '[{levelname}] {message}'
)


def main(argv=None):
    """wetbot's main method"""

    # screw optional colors, just make it beautiful
    # I'll figure out a way to configure it later
    for level, color in LOGGING_COLORS:
        name = logging.getLevelName(level)
        logging.addLevelName(
            level,
            f'{color}{name}{ANSI_RESET}')

    # define a StreamHandler for stdout
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        fmt=LOG_FORMAT_STR_COLOR,
        datefmt='%m-%d %H:%M:%S',
        style='{')
    console_handler.setFormatter(formatter)

    # set up the root logger
    log = logging.getLogger('')
    log.setLevel(logging.DEBUG)
    log.addHandler(console_handler)

    # get bot's SelfUpdatingConfig
    config = get_configuration(argv[1:], console_handler)

    # check for a token
    token = config.get('bot', 'token')
    if not token:
        log.info("please add your bot token to your configuration "
                 "file or pass it via the command line")
        return

    # setup and run the bot
    bot = Wetbot(config)
    bot.run(token)


if __name__ == '__main__':
    main(sys.argv)
