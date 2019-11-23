import logging

import discord
from discord.ext.commands import Cog, Context, command, is_owner

from wetbot.bot import Wetbot

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class OwnerCog(Cog):
    def __init__(self, bot: Wetbot):
        self.bot = bot

    @command(aliases=('eval', 'nevaluate', 'neval'), hidden=True)
    @is_owner()
    async def evaluate(self, ctx: Context, *, msg: str):
        """don't let anyone else touch this one"""
        bot = self.bot  # noqa: F841
        try:
            out = eval(msg)
        except Exception as exception:
            out = '{}: {}'.format(
                type(exception).__name__,
                exception)
        if out == '':
            out = '\u200b'
        if ctx.invoked_with[0] == 'e':
            out = f'```{out}```'
        await ctx.send(str(out))

    @command()
    async def extensions(self, ctx: Context):
        """what crap has she loaded into it today?"""
        await ctx.send('```{}```'.format(
            '\n'.join(sorted(self.bot.extensions.keys()))))

    @command(hidden=True)
    @is_owner()
    async def reload(self, ctx: Context, extension_name: str):
        """you know what it does you built the dang thing"""
        if extension_name in self.bot.extensions:
            await ctx.send(f"reloading extension `{extension_name}`")
            log.info(f"reloading exension '{extension_name}'")
            self.bot.unload_extension(extension_name)
            self.bot.load_extension(extension_name)
        else:
            await ctx.send(f"no extension named `{extension_name}` found")

    @command(hidden=True)
    @is_owner()
    async def load(self, ctx: Context, extension_name: str):
        """games characters and downloads"""
        try:
            self.bot.load_extension(extension_name)
        except ModuleNotFoundError:
            await ctx.send(f"no extension named `{extension_name}` found")
        except discord.errors.ClientException:
            await ctx.send(f"`{extension_name}` is not a valid extension")
        else:
            await ctx.send(f"loaded extension `{extension_name}`")
            log.info(f"loaded extension '{extension_name}`")

    @command(hidden=True)
    @is_owner()
    async def unload(self, ctx, extension_name):
        """backbreaking labor"""
        if extension_name in self.bot.extensions:
            await ctx.send(f"unloading extension `{extension_name}`")
            log.info(f"unloading extension '{extension_name}'")
            self.bot.unload_extension(extension_name)
        else:
            await ctx.send(f"no extension named `{extension_name}` found")


def setup(bot: Wetbot):
    log.info("adding OwnerCog to bot")
    bot.add_cog(OwnerCog(bot))
