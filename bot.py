import discord
from discord.ext import commands
import random
import os
from keep_alive import keep_alive
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="*", intents=intents)
from datetime import datetime
import asyncio
server_id = int(os.getenv("SERVER_ID"))
raw_birthdays = os.getenv("BIRTHDAYS")
birthdays = {}

if raw_birthdays:
    for entry in raw_birthdays.split(","):
        user_id, date = entry.split(":")
        day, month = map(int, date.split("/"))
        birthdays[int(user_id)] = (day, month)


async def birthday_check():
    await bot.wait_until_ready()

    guild = bot.get_guild(server_id)
    channel = guild.system_channel if guild else None

    while not bot.is_closed():
        now = datetime.now()

        for user_id, (day, month) in birthdays.items():
            if now.day == day and now.month == month:
                user = await bot.fetch_user(user_id)
                if channel:
                    await channel.send(
                        f"🎂🧸 Happy Birthday {user.mention}!💗 "
                    )

        await asyncio.sleep(86400)

# Cute messages
encouragements = [
    "You're doing amazing 💗",
    "I'm proud of you 🧸",
    "Don't forget to rest 🌿",
    "You're enough just as you are ✨",
    "Sending you a cozy hug 🤗"
]

# When bot is ready
@bot.event
async def on_ready():
    print(f"{bot.user} is ready 🧸")
    bot.loop.create_task(birthday_check())

# When someone joins
@bot.event
async def on_member_join(member):
    channel = member.guild.system_channel
    if channel:
        msg = random.choice(encouragements)
        await channel.send(f"🧸 Welcome {member.mention}! {msg}")

# When someone leaves
@bot.event
async def on_member_remove(member):
    channel = member.guild.system_channel
    if channel:
        await channel.send(f"🧸 {member.name} left… we’ll miss you 💔")

# Command to get encouragement
@bot.command()
async def hug(ctx, member: discord.Member = None):
    msg = random.choice(encouragements)

    if member:
        await ctx.send(f"🧸 {ctx.author.mention} hugs {member.mention}! {msg}")
    else:
        await ctx.send(f"🧸 {ctx.author.mention} {msg}")

keep_alive()
bot.run(os.getenv("TOKEN"))