import copy
import logging
import random
import re

import discord
from discord.ext import commands

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class SPostCog(commands.Cog):
    wang = re.compile(
        (r'(\b|_)'
         r'('
         r'([bh]?w)h?[aeo]+[ym]?n+g(e?[ziufdry]?|ing|um)?s?'
         r'(\s*'
         r'([bh]?w)h?[aeo]+[ym]?n+g(e?[ziufdry]?|ing|um)?s?'
         r')*'
         r')'
         r'(\b|_)'
         ),
        re.IGNORECASE
    )

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db.spost

    async def _init(self):
        async for generic in self.db.generic.find():
            self.add_generic(generic)

        async for embed in self.db.embed.find():
            self.add_embed(embed)

        self.patterns = {}
        async for pattern in self.db.pattern.find():
            if pattern.get('distribute'):
                pattern['pattern'] = r'(_|\W)*'.join(
                    c for c in pattern['pattern'])
            if pattern.get('case_sensitive'):
                expression = re.compile(pattern['pattern'])
            else:
                expression = re.compile(pattern['pattern'], re.IGNORECASE)
            self.patterns[pattern['name']] = re.compile(expression)
            self.add_pattern(pattern)

        async def on_message(message):
            if message.author.id == self.bot.user.id:
                return
            match = self.wang.search(message.content)
            if match:
                ctx = await self.bot.get_context(message)
                await ctx.send(match.group(2))
            for name, pattern in self.patterns.items():
                match = pattern.search(message.content)
                if match:
                    message = copy.copy(message)
                    message.content = self.bot.command_prefix + name
                    await self.bot.process_commands(message)

        self.bot.add_listener(on_message)

    @commands.command()
    async def shrug(self, ctx):
        """are you dense?"""
        try:
            await ctx.message.delete()
        except discord.errors.Forbidden:
            pass
        await ctx.send(ctx.author.mention + r' ¯\_(ツ)_/¯s')

    @commands.command()
    async def lenny(self, ctx, *, person_owner_only: discord.Member = None):
        """is explanation really necessary?"""
        try:
            await ctx.message.delete()
        except discord.errors.Forbidden:
            pass
        if person_owner_only and await self.bot.is_owner(ctx.author):
            await ctx.send(person_owner_only.mention + ' ( ͡° ͜ʖ ͡°)s')
        else:
            await ctx.send(ctx.author.mention + ' ( ͡° ͜ʖ ͡°)s')

    @commands.command()
    async def brb(self, ctx):
        """it has a name?!"""
        brb_bans = (await self.db.find_one({'name': 'brb_bans'}))['ids']
        if ctx.author.id in brb_bans:
            await ctx.send("but will you *really* brb?")
        else:
            await ctx.send(
                'https://cdn.discordapp.com/attachments/'
                '263457479239663616/319531749564612617/'
                'stickerline-201503031729571.png'
            )

    # The below continues to be wildly hacky and generally
    # unethical, but I am too lazy to solve the problem in
    # a legitimate way.

    def add_generic(self, doc):
        async def func(self, ctx):
            await ctx.send(random.choice(doc['urls']))
        func.__name__ = doc['name']
        func.__doc__ = doc['doc']
        aliases = doc.get('aliases')
        func = commands.command(
            name=doc['name'],
            aliases=aliases if aliases else []
        )(func)
        func.instance = self
        self.__cog_commands__ += (func,)

    def add_embed(self, doc):
        async def func(self, ctx):
            embed = discord.Embed(
                title=doc['title']
                if 'title' in doc
                else discord.Embed.Empty
            ).set_image(
                url=random.choice(doc['images'])
            )
            if doc.get('footer'):
                embed.set_footer(text=doc['footer'])
            await ctx.send(embed=embed)
        func.__name__ = doc['name']
        func.__doc__ = doc['doc']
        aliases = doc.get('aliases')
        func = commands.command(
            name=doc['name'],
            aliases=aliases if aliases else []
        )(func)
        func.instance = self
        self.__cog_commands__ += (func,)

    def add_pattern(self, doc):
        async def func(self, ctx):
            await ctx.send(random.choice(doc['messages']))
        func.__name__ = doc['name']
        func.__doc__ = 'pattern: ' + doc['pattern']
        aliases = doc.get('aliases')
        seconds = doc.get('seconds')
        if seconds != 0:
            func = commands.cooldown(
                1,
                seconds if seconds else 900,
                commands.BucketType.guild)(func)
        func = commands.command(
            name=doc['name'],
            aliases=aliases if aliases else [],
            hidden=True
        )(func)
        func.instance = self
        self.__cog_commands__ += (func,)


async def create_cog(bot):
    cog = SPostCog(bot)
    await cog._init()
    bot.add_cog(cog)


def setup(bot):
    log.info("adding SPostCog to bot")
    bot.loop.create_task(create_cog(bot))
