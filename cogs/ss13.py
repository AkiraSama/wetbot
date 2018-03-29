import asyncio
import logging
import struct
import textwrap
import urllib.parse
from datetime import datetime, timedelta

import discord
from discord.ext.commands import Context, command, group, is_owner

from wetbot.bot import Wetbot

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

GOON_SERVERS = {
    'goon1': ('goon1.goonhub.com', 26100),
    'goon2': ('goon2.goonhub.com', 26200),
}

THE_GOON = """```
{anger_text}
 __________
(--[ .]-[ .] /
(_______0__)```"""


def goon_query(query):
    return b'\x00\x83' + struct.pack(
        '>H', 6 + len(query)
    ) + b'\x00\x00\x00\x00\x00' + query.encode('ascii') + b'\x00'


class SS13Cog(object):
    def __init__(self, bot: Wetbot):
        self.bot = bot
        self.db = bot.db.ss13

    async def _init(self):
        self.ckey_list = (await self.db.find_one(
            {'name': 'ckey_list'}))['ckeys']
        self.ckey_aliases = (await self.db.find_one(
            {'name': 'ckey_aliases'}))['ckeys']

        for c in range(len(self.ckey_list)):
            if self.ckey_list[c] in self.ckey_aliases:
                self.ckey_list += self.ckey_aliases[self.ckey_list[c]]

    @group(invoke_without_command=True)
    @is_owner()
    async def ckeys(self, ctx: Context):
        """everybehdy i kno

        list all ckeys, or add and remove them with subcommands"""

        ckey_list = sorted(
            (await self.db.find_one(
                {'name': 'ckey_list'}))['ckeys'],
            key=lambda ckey: ckey.lower(),
        )
        await ctx.send(f'```{", ".join(ckey_list)}```')

    @ckeys.command(name='add')
    async def ckeys_add(self, ctx: Context, ckey: str):
        """yes more people"""

        ckey_list = sorted(
            (await self.db.find_one_and_update(
                {'name': 'ckey_list'},
                {'$addToSet': {'ckeys': ckey}},
                return_document=True)
             )['ckeys'],
            key=lambda ckey: ckey.lower(),
        )

        await ctx.send(f'```{", ".join(ckey_list)}```')

    @ckeys.command(name='remove')
    async def ckeys_remove(self, ctx: Context, ckey: str):
        """no, less people"""

        ckey_list = sorted(
            (await self.db.find_one_and_update(
                {'name': 'ckey_list'},
                {'$pull': {'ckeys': ckey}},
                return_document=True)
             )['ckeys'],
            key=lambda ckey: ckey.lower(),
        )

        await ctx.send(f'```{", ".join(ckey_list)}```')

    @command()
    async def goon(self, ctx: Context):
        """something awful this way comes

        retrieves server information for both goonstation servers. seeing one
        or the other is not option. this is because we are trying to do just
        a little to save the RP server"""

        for name, address in GOON_SERVERS.items():
            embed_title = f'{name} (byond://{address[0]}:{address[1]})'

            try:
                # Retrieve status information and admin list.
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(*address), 5.0)

                writer.write(goon_query('?status'))
                await asyncio.wait_for(writer.drain(), 3.0)
                status_response = await asyncio.wait_for(
                    reader.read(4096), 3.0)

                writer.write(goon_query('?admins'))
                await asyncio.wait_for(writer.drain(), 3.0)
                admin_response = await asyncio.wait_for(
                    reader.read(4096), 3.0)

                if writer.can_write_eof():
                    writer.write_eof()
                writer.close()

            except (ConnectionRefusedError, asyncio.TimeoutError):
                # Conenction refused or unable to connect before timeout.
                await ctx.send(embed=discord.Embed(
                    title=embed_title + ' (offline)',
                    color=discord.Color.red()))
                continue

            time = datetime.now()

            for packet in (status_response, admin_response):
                if packet[0:2] != b'\x00\x83':
                    # Packet didn't start with expected bytes.
                    log.warning(
                        f"Malformed packet from server {name}, "
                        f"{address[0]}:{address[1]}.")
                    log.debug(f"Packet contents: {packet}")
                    await ctx.send(
                        "Unknown error retrieving status information for "
                        f"server {name} at {address[0]}:{address[1]}")
                    return

            # Get embed paramters.
            status_len = struct.unpack('>H', status_response[2:4])[0]
            params = urllib.parse.parse_qs(
                status_response[5:status_len+3].decode('ascii')
            )

            # Get admin list.
            admin_len = struct.unpack('>H', admin_response[2:4])[0]
            admins = [
                value[0]
                for key, value
                in urllib.parse.parse_qs(
                    admin_response[5:admin_len+3].decode('ascii')
                ).items()
                if key != 'admins'
            ]

            for a in range(len(admins)):
                if admins[a] in self.ckey_aliases:
                    admins += self.ckey_aliases[admins[a]]
                else:
                    log.info('unaliased admin: ' + admins[a])
            players = ', '.join(
                ('\\\u2b50' if player in admins else '') +
                ('\\\U0001f354' if player in self.ckey_list else '') +
                player
                for player
                in sorted(
                    params['player' + str(x)][0]
                    for x
                    in range(
                        int(params['players'][0])
                    )
                )
            )

            try:
                shuttle = int(params['shuttle_time'][0])
                shuttle = str(timedelta(
                    seconds=abs(shuttle)
                )) + (
                    ' (station)'
                    if shuttle < 0
                    else (
                        ' (in transit)'
                        if shuttle not in (0, 600)
                        else ''
                    )
                )
            except ValueError:
                shuttle = params['elapsed'][0]

            try:
                elapsed = str(timedelta(seconds=int(params['elapsed'][0])))
            except ValueError:
                elapsed = params['elapsed'][0]

            await ctx.send(embed=discord.Embed(
                title=embed_title,
                type='rich',
                timestamp=time,
                color=discord.Color.green()
            ).add_field(
                name='Version',
                value=params['version'][0]
            ).add_field(
                name='Mode',
                value=params['mode'][0] + (
                    ', respawn enabled'
                    if params['respawn'][0] == '1'
                    else ''
                )
            ).add_field(
                name='Map Name',
                value=params['map_name'][0]
            ).add_field(
                name='Round Length',
                value=elapsed
            ).add_field(
                name='Shuttle Time',
                value=shuttle
            ).add_field(
                name='Station Name',
                value=(params['station_name'][0]
                       if params.get('station_name')
                       else 'N/A')
            ).add_field(
                name='Players ({})'.format(params['players'][0]),
                value=players if players else 'N/A',
                inline=False
            ))

    @command()
    async def goonsay(self, ctx: Context, *,
                      anger_text: str = "A clown? On a space station? what"):
        """not sure why im making this"""
        anger_text = textwrap.fill(
            anger_text[0:min(len(anger_text), 200)]
        )
        await ctx.send(THE_GOON.format(anger_text=anger_text))


async def create_cog(bot: Wetbot):
    cog = SS13Cog(bot)
    await cog._init()
    bot.add_cog(cog)


def setup(bot: Wetbot):
    log.info("adding SS13Cog to bot")
    bot.loop.create_task(create_cog(bot))
