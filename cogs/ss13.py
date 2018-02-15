import asyncio
import logging
import struct
import urllib.parse
from datetime import datetime, timedelta

import discord
from discord.ext import commands

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

class SS13Cog(object):
    @staticmethod
    def goon_query(query):
        return b'\x00\x83' + struct.pack(
            '>H', 6 + len(query)
        ) + b'\x00\x00\x00\x00\x00' + query.encode('ascii') + b'\x00'

    def __init__(self, bot):
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

    @commands.command()
    async def goon(self, ctx):
        """something awful this way comes"""
        for name, address in {'goon1': ('goon1.goonhub.com', 26100), 'goon2': ('goon2.goonhub.com', 26200)}.items():
            title = f'{name} (byond://{address[0]}:{address[1]})'
            try:
                r, w = await asyncio.wait_for(asyncio.open_connection(*address), 5.0)
                w.write(self.goon_query('?status'))
                await asyncio.wait_for(w.drain(), 3.0)
                response = await asyncio.wait_for(r.read(4096), 3.0)
                w.write(self.goon_query('?admins'))
                await asyncio.wait_for(w.drain(), 3.0)
                adsponse = await asyncio.wait_for(r.read(4096), 3.0)
            except (ConnectionRefusedError, asyncio.TimeoutError):
                await ctx.send(embed=discord.Embed(title=title + ' (offline)', color=discord.Color.red()))
                continue
            if w.can_write_eof(): w.write_eof()
            w.close()
            time=datetime.now()

            if response[0:2] != b'\x00\x83':
                return

            l = struct.unpack('>H', response[2:4])[0]
            params = urllib.parse.parse_qs(response[5:l+3].decode('ascii'))
            l = struct.unpack('>H', adsponse[2:4])[0]
            admins = [value[0] for key, value in urllib.parse.parse_qs(adsponse[5:l+3].decode('ascii')).items() if key != 'admins']
            for a in range(len(admins)):
                if admins[a] in self.ckey_aliases:
                    admins += self.ckey_aliases[admins[a]]
                else:
                    log.info('unaliased admin: ' + admins[a])
            players = ', '.join(
                    ('\\\u2b50' if p in admins else '') +
                    ('\\\U0001f354' if p in self.ckey_list else '') +
                    p for p in sorted(params['player' + str(x)][0] for x in range(int(params['players'][0]))))
            try:
                shuttle = int(params['shuttle_time'][0])
                shuttle = str(timedelta(seconds=abs(shuttle))) + (' (station)' if shuttle < 0 else (' (in transit)' if shuttle not in (0, 600) else ''))
            except ValueError:
                shuttle = params['elapsed'][0]
            try:
                elapsed = str(timedelta(seconds=int(params['elapsed'][0])))
            except ValueError:
                elapsed = params['elapsed'][0]
            await ctx.send(embed=discord.Embed(
                title=title, type='rich', timestamp=time, color=discord.Color.green()).add_field(
                name='Version', value=params['version'][0]).add_field(
                name='Mode', value=params['mode'][0] + (', respawn enabled' if params['respawn'][0] == '1' else '')).add_field(
                name='Map Name', value=params['map_name'][0]).add_field(
                name='Round Length', value=elapsed).add_field(
                name='Shuttle Time', value=shuttle).add_field(
                name='Station Name', value=params['station_name'][0] if params.get('station_name') else 'N/A').add_field(
                name='Players ({})'.format(params['players'][0]), value=players if players else 'N/A', inline=False))

async def create_cog(bot):
    cog = SS13Cog(bot)
    await cog._init()
    bot.add_cog(cog)

def setup(bot):
    log.info("adding SS13Cog to bot")
    bot.loop.create_task(create_cog(bot))

