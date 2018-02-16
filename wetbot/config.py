import argparse
import json
import logging
from collections import OrderedDict
from pathlib import Path

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class SelfUpdatingConfig(object):
    def __init__(self, filepath, args=None, default_section=''):
        self._filepath = Path(filepath)
        self._args = args
        self._default_section = default_section
        self._config = OrderedDict()
        self.read()

    def _create(self):
        log.info("no configuration file found at specified path")
        log.info("attempting to create configuration file at "
                 "'{}'".format(self._filepath))
        log.debug("attempting to create parent directories")
        self._filepath.parent.mkdir(parents=True, exist_ok=True)
        log.debug("attempting to touch file (umask 0o666)")
        self._filepath.touch(0o600)
        log.info("touched file '{}'".format(self._filepath))

    def read(self):
        log.info("attempting to load configuration from '{}'".format(
            self._filepath))
        try:
            with self._filepath.open(mode='r') as f:
                self._config = json.load(f, object_pairs_hook=OrderedDict)
        except FileNotFoundError:
            # watch this get stuck in a recursive loop someday
            self._create()
            self.write()
            self.read()
        except json.decoder.JSONDecodeError:
            # watch this happen all the time because I'm not careful
            log.exception("unable to load configuration from file:")
            log.error("file may have become corrupted or been "
                      "incorrectly modified")
            self._config = None
        else:
            log.info("configuration loaded successfully")

    def write(self):
        log.info("attempting to write configuration to '{}'".format(
            self._filepath))
        with self._filepath.open(mode='w') as f:
            json.dump(self._config, f, indent='  ')
        log.info("configuration saved successfully")

    def get(self, section, value, default=''):
        if self._args and section == self._default_section:
            if value in self._args and self._args[value] is not None:
                log.debug("requested value '{}' found in arguments with "
                          "a value of '{}'".format(
                              value, self._args[value]))
                return self._args[value]
        if self._config is None:
            # this is a massive cop out for now
            raise AttributeError()
        if section not in self._config:
            log.debug("created section '{}'".format(section))
            self._config[section] = OrderedDict()
        if value not in self._config[section]:
            log.debug("assigned default value '{}' to value '{}' in "
                      "section '{}'".format(default, value, section))
            self._config[section][value] = default
            self.write()
        return self._config[section][value]


parser = argparse.ArgumentParser(
    description="wetbot - a discord.py based personal bot")
parser.add_argument('--config', action='store',
                    default='./data/config/wetbot.cfg',
                    help="filepath to configuration file",
                    metavar='FILEPATH', dest='config_file')
parser.add_argument('-v', '--verbose', action='store_true',
                    help="increase output verbosity")
parser.add_argument('token', action='store', nargs='?',
                    help="bot user token")
parser.add_argument('--owner', action='store', default=None, type=int,
                    help="bot owner user id",
                    metavar='OWNER_ID', dest='owner_id')
parser.add_argument('--prefix', action='store', default=None,
                    help="command prefix string",
                    dest='command_prefix')


def get_configuration(argv, log_handler):
    args = parser.parse_args(argv)
    if args.verbose:
        log_handler.setLevel(logging.DEBUG)
        log.debug("set logging level to DEBUG")

    return SelfUpdatingConfig(args.config_file, vars(args), 'bot')
