import asyncio
import logging
import random
import re
from datetime import datetime, timedelta

from discord.ext.commands import Context, command, clean_content

from wetbot.bot import Wetbot

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

ROLL_CHECK = re.compile(
    (r'(\b)'
     r'(?P<roll>'
     r'(?P<dice>\d*)d'
     r'(?P<sides>\d+|%)'
     r'(?P<sign>[+-])?(?P<modifier>\d*)'
     r'(?:dc)?(?P<threshold>\d*)'
     r')'
     r'($|\s)'
     ),
    re.IGNORECASE)

TIME_FORMAT = re.compile(
    r'('
    r'((?P<days>\d+)d)?'
    r'((?P<hours>\d+)h)?'
    r'((?P<minutes>\d+)m)?'
    r'((?P<seconds>\d+)s)?'
    r')'
)

POLL_PERIOD = 3600


class UtilCog(object):
    def __init__(self, bot: Wetbot):
        self.bot = bot
        self.db = bot.db.util
        self._polling_future = bot.loop.create_task(self.poll_reminders())
        self._reminders = []

    def __unload(self):
        futures = asyncio.gather(
            self._polling_future,
            *self._reminders,
            return_exceptions=True,
        )
        try:
            futures.cancel()
        except asyncio.CancelledError:
            pass

    @command(aliases=['c'])
    async def choose(self, ctx: Context, *, pipe_separated_choices: str):
        """PROGRAMMED VERY FAST

        example usage:
        !choose one | two | three"""
        if random.random() > 0.95:
            await ctx.send("yes")
            return
        choices = pipe_separated_choices.split('|')
        await ctx.send('**{}**'.format(random.choice(choices).strip()))

    @command()
    async def roll(self, ctx: Context, *, expressions: str):
        """roll dice for numbers

        Matches to the expression:
        ``[die]d<sides>[+/-<modifier>][dc<threshold>]``
        Where...
        die       == number of die to roll  (1 if none)
        sides     == number of sides per die (100 if %)
        modifier  == number to add to each result
        threshold == number required for roll to succeed

        Note that the only required elements are the 'd' and the number of
        sides. Everything else can be included or disincluded at your leisure.
        """
        dice_rolls = []
        while ROLL_CHECK.match(expressions):
            dice_roll, *expressions = expressions.split(maxsplit=1)
            expressions = expressions[0] if expressions else ''
            dice_rolls.append(ROLL_CHECK.match(dice_roll))
        results = ctx.author.mention
        if not dice_rolls:
            await ctx.send(results + " I can't roll that doofus")
            return
        for dice_roll in dice_rolls:
            rolls = []

            dice = (int(dice_roll.group('dice'))
                    if dice_roll.group('dice')
                    else 1)

            sides = (100
                     if dice_roll.group('sides') == '%'
                     else int(dice_roll.group('sides')))

            for _ in range(dice):
                num = random.randrange(sides) + 1
                if dice_roll.group('modifier'):
                    modifier = int(dice_roll.group('modifier'))
                    if dice_roll.group('sign') == '-':
                        modifier *= -1
                    num += modifier
                rolls.append(num)

            roll_sum = sum(rolls)
            threshold = dice_roll.group('threshold')
            if len(rolls) > 1:
                end = ' ({})'.format(', '.join(
                    str(roll) + (
                        ('**\u2713**'
                         if int(threshold) <= roll
                         else '\u2718')
                        if threshold else ''
                    ) for roll in rolls
                ))
            else:
                if threshold:
                    end = ('**\u2713**'
                           if int(threshold) <= roll_sum
                           else '\u2718')
                else:
                    end = ''

            results += ' {roll} = {sum}{end}'.format(
                roll=dice_roll.group('roll'),
                sum=roll_sum,
                end=end,
            )
        await ctx.send('{results}{rest}'.format(
            results=results,
            rest=f' **{expressions}**' if expressions else ''
        ))

    async def schedule_reminder(self, reminder_doc):
        date = datetime.fromtimestamp(reminder_doc['timestamp'])
        diff = date - datetime.utcnow()
        if diff <= timedelta(POLL_PERIOD):
            async def reminder():
                await asyncio.sleep(diff.total_seconds())
                delete_result = await self.db.reminders.delete_one(
                    {'_id': reminder_doc['_id']})
                if delete_result.deleted_count == 0:
                    return
                channel = self.bot.get_channel(
                    reminder_doc['channel_id'])
                mention = self.bot.get_user(
                    reminder_doc['user_id']).mention
                text = reminder_doc['text']
                await channel.send(
                    f"{mention} {text}")
            self._reminders.append(
                self.bot.loop.create_task(reminder())
            )

    async def poll_reminders(self):
        while True:
            async for reminder in self.db.reminders.find():
                await self.schedule_reminder(reminder)
            await asyncio.sleep(POLL_PERIOD)

    @command()
    async def remind(self, ctx: Context,
                     time_delay: str, *,
                     reminder_text: clean_content()
                     ):
        """https://www.youtube.com/watch?v=YVkUvmDQ3HY

        takes a time_delay in the format of
        ``[days]d[hours]h[minutes]m[seconds]``

        still limited to 14 days because I don't wanna deal with
        absolute loads of reminders for future dates clogging up
        my database atm
        """

        delay = TIME_FORMAT.match(time_delay)
        delay_dict = {
            key: int(value)
            for key, value
            in delay.groupdict(default=0).items()
        }

        delta = timedelta(**delay_dict)
        if delta == timedelta(0):
            await ctx.send("invalid timestring!")
            return
        if delta > timedelta(days=14):
            await ctx.send("nnnnnnno")
            return
        remind_time = datetime.utcnow() + delta

        doc = {
            'timestamp': remind_time.timestamp(),
            'text': reminder_text,
            'channel_id': ctx.channel.id,
            'user_id': ctx.author.id,
        }

        result = await self.db.reminders.insert_one(doc)
        doc['_id'] = result.inserted_id

        await self.schedule_reminder(doc)
        await ctx.send(f"I'll remind you about that in {delta}")


def setup(bot: Wetbot):
    log.info("adding UtilCog to bot")
    bot.add_cog(UtilCog(bot))
