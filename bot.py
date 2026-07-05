import discord
from discord.ext import commands
import random
import os
from keep_alive import keep_alive
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="*", intents=intents)

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