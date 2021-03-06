import json
import logging
import urllib.parse

from aiohttp import ClientSession

from discord.ext.commands import Cog, Context, command

from wetbot.bot import Wetbot

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

WIKIPEDIA_URL = 'https://en.wikipedia.org/w/api.php'
UD_URL = 'http://api.urbandictionary.com/v0/define?term={}'
OXFORD_URL = 'https://od-api.oxforddictionaries.com/api/v1'

DEF_TEMPLATE = (
    '```\n{word}{domains}\n/{pronunciation}/, '
    '{category}\n{definition}```'
)


def json_format(response):
    return '```json\n{}```'.format(
        json.dumps(response, indent='  '))


class InfoCog(Cog):
    def __init__(self, bot: Wetbot):
        self.bot = bot
        self.session = ClientSession(loop=bot.loop)
        self.active_definitions = {}

    def __unload(self):
        self.bot.loop.create_task(self.session.close())

    async def _wiki_get_pageid(self, query: str):
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
                log.debug(f"wikipedia search response: {response}")
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
                                r"I got nothin ¯\_(ツ)_/¯")
                else:
                    return (
                        None,
                        json_format(response))

    @command(aliases=('wiki', 'w'))
    async def wikipedia(self, ctx: Context, *, query: str):
        """search all the knowledge"""
        pageid, error = await self._wiki_get_pageid(query)

        if pageid is None:
            await ctx.send(error)
            return

        query_string = ('?action=query'
                        '&prop=info|pageprops|links'
                        '&pllimit=max'
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
                log.debug(f"wikipedia info response: {results}")
                if results:
                    page = results['pages'][pageid]
                    if 'disambiguation' not in page['pageprops']:
                        out = results['pages'][pageid]['canonicalurl']
                    else:
                        out = "try something like... ```{titles}```".format(
                            titles=', '.join(
                                (link['title']
                                 if ',' not in link['title']
                                 else '"{}"'.format(link['title']))
                                for link in page['links']
                                if not any(
                                    link['title'].startswith(s)
                                    for s in (
                                        'Talk:',
                                        'Help:',
                                        'Wikipedia:'
                                    )
                                )
                            )
                        )
                else:
                    out = json_format(response)

        await ctx.send(out)

    @command(aliases=('ud',))
    async def urbandictionary(self, ctx: Context, *, query: str):
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
                elif results is not None or response.get('result_type') == 'no_results':
                    out = r"I got nothin ¯\_(ツ)_/¯"
                else:
                    out = json_format(response)
            else:
                out = json_format(response)

        await ctx.send(out)

    domain_str = lambda self, domains: ' ({})'.format(', '.join(domains))
    def iterate_definitions(self, response: dict):  # noqa: E301
        return_dict = {
            'word': '',
            'domains': '',
            'pronunciation': '',
            'category': '',
            'definition': ''
        }
        for lexical_entry in response['lexicalEntries']:
            # set word
            return_dict['word'] = lexical_entry['text']

            # set category
            return_dict['category'] = lexical_entry['lexicalCategory'].lower()

            # set pronunciation, if it exists
            if 'pronunciations' in lexical_entry:
                return_dict['pronunciation'] = '/ ᴏʀ /'.join(
                    (p['phoneticSpelling']
                     if 'phoneticSpelling' in p
                     else '(no pronunciation)')
                    for p
                    in lexical_entry['pronunciations']
                )
            else:
                return_dict['pronunciation'] = '(no pronunciation)'

            # handle case of derivative entry
            parent = lexical_entry.get('derivativeOf')
            if parent:
                return_dict['definition'] = 'see {}'.format(
                    ', '.join(
                        derivative['text'] for derivative in parent))
                yield return_dict
                continue

            # process all entries
            for entry in lexical_entry['entries']:
                # process senses of entry
                for sense in entry['senses']:
                    # process definitions, if they exist
                    if 'definitions' in sense:
                        for definition in sense['definitions']:
                            return_dict['domains'] = (
                                self.domain_str(sense['domains'])
                                if 'domains' in sense
                                else '')
                            return_dict['definition'] = definition
                            yield return_dict

                    # process subsenses, if they exist
                    if 'subsenses' in sense:
                        for subsense in sense['subsenses']:
                            # more definitions, inside the subsenses
                            for definition in subsense['definitions']:
                                return_dict['domains'] = (
                                    self.domain_str(subsense['domains'])
                                    if 'domains' in subsense
                                    else '')
                                return_dict['definition'] = definition
                                yield return_dict

    @command(aliases=('d',))
    async def define(self, ctx: Context, *, query: str = None):
        """mommy fixed it

        after requesting a definition, use the command with no query
        in the same channel to cycle through additional meanings"""
        if not query:
            try:
                if ctx.channel.id in self.active_definitions:
                    await ctx.send(DEF_TEMPLATE.format(
                        **next(self.active_definitions[
                            ctx.channel.id
                        ])))
                    return
                else:
                    await ctx.send("no active definitions!")
            except StopIteration:
                await ctx.send("ran outta definitions, friend")
                del self.active_definitions[ctx.channel.id]
                return

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
                    await ctx.send(r"I got nothin ¯\_(ツ)_/¯")
                    return

        async with self.session.get(
            OXFORD_URL + '/entries/en/' + word_id,
            headers=headers,
            timeout=5
        ) as resp:
            if resp.status == 200:
                result = (await resp.json())['results'][0]
            else:
                await ctx.send(json_format(await resp.json()))
                return

        self.active_definitions[ctx.channel.id] = (
            self.iterate_definitions(result)
        )

        try:
            await ctx.send(DEF_TEMPLATE.format(
                **next(self.active_definitions[ctx.channel.id])
            ))
        except StopIteration:
            await ctx.send("there is not even *one* of that thing")


def setup(bot: Wetbot):
    log.info("adding InfoCog to bot")
    bot.add_cog(InfoCog(bot))
