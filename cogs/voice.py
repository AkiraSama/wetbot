import logging

from discord import Member
from discord.ext.commands import Cog, Context, command, is_owner

from wetbot.bot import Wetbot

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class VoiceCog(Cog):
    def __init__(self, bot: Wetbot):
        self.bot = bot

    @command()
    @is_owner()
    async def kill(self, ctx: Context, *, member: Member):
        """nani?!"""
        
        execution_channel_id = self.bot.config.get(
            'voice', 'execution_channel_id', None)
        if not execution_channel_id:
            execution_channel = await ctx.guild.create_voice_channel(
                'Slime Chamber',
                category=self.bot.get_channel(360649655815766016)
            )
            self.bot.config.set(
                'voice', 'execution_channel_id', execution_channel.id)
        else:
            execution_channel = self.bot.get_channel(
                execution_channel_id)

        await member.move_to(execution_channel)
        await execution_channel.delete()

        execution_channel = await ctx.guild.create_voice_channel(
            'Slime Chamber',
            category=self.bot.get_channel(360649655815766016)
        )
        self.bot.config.set(
            'voice', 'execution_channel_id', execution_channel.id)
            

def setup(bot: Wetbot):
    log.info("adding VoiceCog to bot")
    bot.add_cog(VoiceCog(bot))
