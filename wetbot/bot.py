import copy
import logging
import traceback
from pathlib import Path

import discord
from discord.ext import commands

from motor.motor_asyncio import AsyncIOMotorClient

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class Wetbot(commands.Bot):
    def __init__(self, config, formatter=None, **options):
        self._config = config
        self._db = AsyncIOMotorClient().wetbot
        super().__init__(
            command_prefix=config.get(
                'bot', 'command_prefix', '!'),
            formatter=formatter,
            description=config.get(
                'bot', 'description', False),
            pm_help=config.get(
                'bot', 'pm_help', False),
            owner_id=config.get(
                'bot', 'owner_id', None),
            **options)
        self.pm_channel = None

        cog_dir = Path('./cogs')
        cog_dir.mkdir(exist_ok=True)
        log.info(f"loading cogs from directory {cog_dir}")
        for ex in cog_dir.iterdir():
            if ex.suffix == '.py':
                path = '.'.join(ex.with_suffix('').parts)
                log.info(f"attempting to load extension '{path}'")
                self.load_extension(path)

    @property
    def config(self):
        return self._config

    @property
    def db(self):
        return self._db

    async def on_ready(self):
        log.info(
            "{}[{}] connected to discord 'cause she cares. "
            "Bite me.".format(
                self.user.name,
                self.user.id))

        self.pm_channel = self.get_channel(self.config.get(
            'bot', 'pm_channel', None))

    async def on_message(self, message):
        if isinstance(message.channel, discord.abc.PrivateChannel):
            await self.pm_channel.send('{}: {}'.format(
                message.author,
                message.content))
        await self.process_commands(message)

    async def on_command_error(self, ctx, error):
        log.warn('Adorably ignoring exception in command "{}":\n{}'.format(
            ctx.command,
            ''.join(traceback.format_exception(
                type(error),
                error,
                error.__traceback__))))

    async def help_redirect(self, ctx, topic):
        message = copy.copy(ctx.message)
        message.content = self.command_prefix + 'help ' + topic
        await self.process_commands(message)
