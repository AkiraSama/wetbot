import aiohttp
import json
import logging
import urllib.parse

import discord
from discord.ext import commands

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

WIKIPEDIA_URL = 'https://en.wikipedia.org/w/api.php'
UD_URL = 'http://api.urbandictionary.com/v0/define?term={}'
OXFORD_URL = 'https://od-api.oxforddictionaries.com/api/v1'

def json_format(response):
    return '```json\n{}```'.format(
        json.dumps(response, indent='  '))

class InfoCog(object):
    def __init__(self, bot):
        self.bot = bot
        self.session = bot.http._session

    async def _wiki_get_pageid(self, query):
        query = urllib.parse.quote_plus(query)
        query_string = ('?action=query'
                        '&list=search'
                        '&format=json'
                        '&srsearch={}'
                        '&srinfo=suggestion'
                        '&srprop=redirecttitle')

        async with self.session.get(
            WIKIPEDIA_URL + query_string.format(query),
            timeout=5
        ) as resp:
            if resp.status == 200:
                response = await resp.json()
                results = response.get('query')
                if results:
                    if results['search']:
                        return (str(results['search'][0]['pageid']), None)
                    else:
                        try:
                            return await self._wiki_get_pageid(
                                results['searchinfo']['suggestion'])
                        except KeyError:
                            return (
                                None,
                                "I got nothin ¯\_(ツ)_/¯")
                else:
                    return (
                        None,
                        json_format(response))

    @commands.command(aliases=('wiki', 'w'))
    async def wikipedia(self, ctx, *, query):
        """search all the knowledge"""
        pageid, error = await self._wiki_get_pageid(query)

        if pageid is None:
            await ctx.send(error)
            return

        query_string = ('?action=query'
                        '&prop=info'
                        '&format=json'
                        '&pageids={}'
                        '&inprop=url')
        
        async with self.session.get(
            WIKIPEDIA_URL + query_string.format(pageid),
            timeout=5
        ) as resp:
            if resp.status == 200:
                response = await resp.json()
                results = response.get('query')
                if results:
                    out = results['pages'][pageid]['canonicalurl']
                else:
                    out = json_format(response)

        await ctx.send(out)

    @commands.command(aliases=('ud',))
    async def urbandictionary(self, ctx, *, query):
        """search all the OTHER knowledge"""
        async with self.session.get(
            UD_URL.format(urllib.parse.quote(query)),
            timeout=5
        ) as resp:
            if resp.status == 200:
                response = await resp.json()
                results = response.get('list')
                if results:
                    out = ('http://urbandictionary.com/define.php?term=' +
                           urllib.parse.quote(results[0]['word']))
                elif response.get('result_type') == 'no_results':
                    out = "I got nothin ¯\_(ツ)_/¯"
                else:
                    out = json_format(response)

        await ctx.send(out)

    @commands.command(aliases=('d',))
    async def define(self, ctx, *, query):
        """mommy fixed it"""
        app_id = self.bot.config.get('oxford_dictionaries', 'app_id', '')
        app_key = self.bot.config.get('oxford_dictionaries', 'app_key', '')
        if not app_id or not app_key:
            await ctx.send("configuration incomplete")
            return
        headers = {
            'app_id': app_id,
            'app_key': app_key
        }

        word_id = None
        async with self.session.get(
            OXFORD_URL + '/search/en?q=' + urllib.parse.quote(query),
            headers=headers,
            timeout=5
        ) as resp:
            if resp.status == 200:
                response = await resp.json()
                if response['metadata']['total'] > 0:
                    word_id = response['results'][0]['id']
                else:
                    await ctx.send("I got nothin ¯\_(ツ)_/¯")
                    return

        async with self.session.get(
            OXFORD_URL + '/entries/en/' + word_id,
            headers=headers,
            timeout=5
        ) as resp:
            if resp.status == 200:
                result = (await resp.json())['results'][0]

        entry = result['lexicalEntries'][0]
        d = (
            '```\n{word}\n/{pronunciation}/, '
            '{category}\n{definition}```'
        ).format(
            word=entry['text'],
            pronunciation='/ ᴏʀ /'.join(
                p['phoneticSpelling']
                for p
                in entry['pronunciations']),
            category=entry['lexicalCategory'].lower(),
            definition=entry['entries'][0]['senses'][0]['definitions'][0]
        )

        await ctx.send(d)

def setup(bot):
    log.info("adding InfoCog to bot")
    bot.add_cog(InfoCog(bot))

