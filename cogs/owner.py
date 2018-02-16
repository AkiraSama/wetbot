import logging

import discord
from discord.ext import commands

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class OwnerCog(object):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=('eval', 'nevaluate', 'neval'), hidden=True)
    @commands.is_owner()
    async def evaluate(self, ctx, *, msg):
        """don't let anyone else touch this one"""
        bot = self.bot # noqa: F841
        try:
            out = eval(msg)
        except Exception as e:
            out = '{}: {}'.format(type(e).__name__, e)
        if out == '':
            out = '\u200b'
        if ctx.invoked_with[0] == 'e':
            out = f'```{out}```'
        await ctx.send(str(out))

    @commands.command()
    async def extensions(self, ctx):
        """what crap has she loaded into it today?"""
        await ctx.send('```{}```'.format(
            '\n'.join(sorted(self.bot.extensions.keys()))))

    @commands.command(hidden=True)
    @commands.is_owner()
    async def reload(self, ctx, extension):
        """you know what it does you built the dang thing"""
        if extension in self.bot.extensions:
            await ctx.send(f"reloading extension `{extension}`")
            log.info(f"reloading exension '{extension}'")
            self.bot.unload_extension(extension)
            self.bot.load_extension(extension)
        else:
            await ctx.send(f"no extension named `{extension}` found")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def load(self, ctx, extension):
        """games characters and downloads"""
        try:
            self.bot.load_extension(extension)
        except ModuleNotFoundError:
            await ctx.send(f"no extension named `{extension}` found")
        except discord.errors.ClientException:
            await ctx.send(f"`{extension}` is not a valid extension")
        else:
            await ctx.send(f"loaded extension `{extension}`")
            log.info(f"loaded extension '{extension}`")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def unload(self, ctx, extension):
        """backbreaking labor"""
        if extension in self.bot.extensions:
            await ctx.send(f"unloading extension `{extension}`")
            log.info(f"unloading extension '{extension}'")
            self.bot.unload_extension(extension)
        else:
            await ctx.send(f"no extension named `{extension}` found")


def setup(bot):
    log.info("adding OwnerCog to bot")
    bot.add_cog(OwnerCog(bot))
