import copy
import logging

import discord
from discord.ext import commands

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

class TerrariaCog(object):
    def __init__(self, bot):
        self.bot = bot
        self.session = bot.http._session

    @commands.group(aliases=('terr', 'terrararar'))
    async def terraria(self, ctx):
        """rawrrwarrwarrwarrwarrwarrwarrwar"""
        if ctx.invoked_subcommand is None:
            message = copy.copy(ctx.message)
            message.content = self.bot.command_prefix + 'terraria status'
            await self.bot.process_commands(message)

    @terraria.command(name='status')
    async def terraria_status(self, ctx, rules=None):
        ip = self.bot.config.get('terraria', 'ip', None)
        port = self.bot.config.get('terraria', 'port', 7878)
        token = self.bot.config.get('terraria', 'token', None)
        if ip is None or token is None:
            log.info("Terraria API configuration is incomplete")
            await ctx.send("configration incomplete")
            return

        async with self.session.get(
            (f'http://{ip}:{port}/v2/server/status'
             f'?rules={"true" if rules else "false"}'
             f'&players=true&token={token}'),
            timeout=5
        ) as resp:
            if resp.status == 200:
                response = await resp.json()

        embed = discord.Embed(
            title=f"Terraria Server ({response['uptime']})",
            color=discord.Color.green()
        ).add_field(
            name='world',
            value=response['world']
        ).add_field(
            name='version',
            value=response['serverversion']
        ).add_field(
            inline=False,
            name='players ({players}/{maxplayers})'.format(
                players=response['playercount'],
                maxplayers=response['maxplayers']),
            value=(', '.join(player['nickname'] + (
                '' if player['active'] else ' (inactive)'
            ) for player in response['players'])
                   if response['players']
                   else 'N/A')
        )
        
        rules = response.get('rules')
        if rules:
            for name, value in sorted(rules.items()):
                embed.add_field(name=name, value=value)
        await ctx.send(embed=embed)

def setup(bot):
    log.info("adding TerrariaCog to bot")
    bot.add_cog(TerrariaCog(bot))

