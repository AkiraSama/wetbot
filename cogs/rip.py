import logging
import random

import discord
from discord.ext import commands

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

class RipCog(object):
    ME_ALIASES = ('me', 'moi', 'menya', 'mig')

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db.rips
    
    @commands.command()
    async def rip(self, ctx, *, names):
        """ded
        
        where <names> is a comma-separated list of ded individuals"""
        
        for name in (n.strip() for n in names.split(',')):
            if name != 'EVERYONE':
                name = name.lower()
            if name in self.ME_ALIASES:
                name = ctx.author.name.lower()
            out = await self.db.find_one(
                {'names': {'$in': [name]}},
                {'rips': ''})
            if out:
                try:
                    await ctx.send(random.choice(out['rips']))
                except IndexError:
                    return

    @commands.group(hidden=True)
    @commands.is_owner()
    async def rips(self, ctx):
        """manage rip messages"""
        if ctx.invoked_subcommand is None:
            await self.bot.help_redirect(ctx, 'rips')

    @rips.group(name='add')
    async def rips_add(self, ctx):
        """add a value to the database"""
        if (ctx.invoked_subcommand is None or
                ctx.invoked_subcommand.name == 'add'):
            await self.bot.help_redirect(ctx, 'rips add')

    @rips_add.command(name='name')
    async def rips_add_name(self, ctx, *names):
        """add a new name or aliases for an existing name"""
        if not names:
            return
        else:
            names = tuple(n.lower() for n in names)
        c = self.db.find({'names': {'$in': names}}, {'_id': ''})
        count = await c.count()
        if count > 1:
            await ctx.send("name conflict!")
        elif count == 1:
            async for e in c:
                i = e['_id']
            doc = await self.db.find_one_and_update(
                {'_id': i},
                {'$addToSet': {'names': {'$each': names}}},
                {'names': ''},
                return_document=True)
            await ctx.send(', '.join(doc['names']))

        else:
            res = await self.db.insert_one({'names': names, 'rips': []})
            doc = await self.db.find_one(
                {'_id': res.inserted_id}, {'names': ''})
            await ctx.send(', '.join(doc['names']))

    @rips_add.command(name='rip')
    async def rips_add_rip(self, ctx, name, url):
        """add a new rip to a name"""
        res = await self.db.update_one(
            {'names': {'$in': [name]}},
            {'$addToSet': {'rips': url}})
        if res.modified_count == 0:
            await ctx.send('no such name!')
        else:
            await ctx.send('added')

    @rips.group(name='del')
    async def rips_del(self, ctx):
        """remove a value from the database"""
        if (ctx.invoked_subcommand is None or
                ctx.invoked_subcommand.name == 'del'):
            await self.bot.help_redirect(ctx, 'rips del')

    @rips_del.command(name='name')
    async def rips_del_name(self, ctx, *names):
        """remove an alias or entry"""
        if not names:
            return
        else:
            names = tuple(n.lower() for n in names)
        out = []
        while True:
            doc = await self.db.find_one_and_update(
                {'names': {'$in': names}},
                {'$pullAll': {'names': names}},
                {'names': ''},
                return_document=True)
            if doc is None:
                break
            if doc['names']:
                out.append(', '.join(doc['names']))
            else:
                await self.db.delete_one({'_id': doc['_id']})
                out.append('`deleted`')
        if out:
            await ctx.send('\n'.join(out))

    @rips_del.command(name='rip')
    async def rips_del_rip(self, ctx, name, url):
        """remove a rip from a name"""
        res = await self.db.update_one(
            {'names': {'$in': [name]}},
            {'$pull': {'rips': url}})
        if res.modified_count == 0:
            await ctx.send('no such name!')
        else:
            await ctx.send('deleted')

def setup(bot):
    log.info("adding RipCog to bot")
    bot.add_cog(RipCog(bot))

