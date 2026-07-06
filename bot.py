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
SERVER_NAME = os.getenv("SERVER_NAME")
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
                    msg = random.choice(special_bday_messages)
                    await channel.send(
                        f"🎂🧸 Happy Birthday {user.mention}!! 💗 {msg} "
                    )

        await asyncio.sleep(86400)

# Cute messages
special_bday_messages=[
    "🎉 Wishing you a day filled with love, joy, and all the things that make you happiest! 🧸💖",
    "🎉 May your day be as special and wonderful as you are! 🧸✨",
    "🎉 May your year ahead be filled with laughter, love, and endless adventures! 🧸🌟",
    "🎉 Wishing your day to be as sweet and delightful as you are! 🧸🍰"

]

adjectives = ["warm", "cozy", "gentle", "soft", "snuggly"]

encouragements = [
    "You're doing amazing 💗",
    "I'm proud of you 🧸",
    "Take it easy today 🌿",
    "You're enough just as you are ✨",
    "Sending lots of love your way 💖",
]

welcome_messages = [
    "Glad to have you here! 💖",
    "Hope you have a great time! 🌟",
    "Hope you're ready to relax! 🧸",
    "The cozy vibes are immaculate here! ✨"
]

gone_messages = [
    "we’ll miss you 💔",
    "hope to see you again soon! 🩹",
    "take care of yourself! 🌿",
    "your legacy will live on in our hearts 💖"
]
        
mysteries = [
    "Why is water wet?",
    "What is the meaning of life?",
    "Why do cats purr?",
    "What is love?",
    "Why do we dream?",
    "What is the sound of one hand clapping?"
] 

dreams =[
    "a world made of candy and chocolate 🍭🍫",
    "a magical forest filled with talking animals and fairies 🧚‍♂️🦊",
    "a cozy cabin in the mountains with a warm fireplace and a view of the stars 🏔️✨", 
    "a beach with crystal clear water and soft sand, where you can relax and listen to the waves 🌊🏖️",
    "a whimsical carnival with colorful rides, games, and cotton candy 🎡🍿",
    "an epic adventure through space, exploring new planets and galaxies 🚀🌌",
    "a peaceful garden filled with blooming flowers and chirping birds 🌸🐦",
]


drinks = [
    "warm cup of tea 🍵",
    "refreshing glass of lemonade 🍋",
    "warm mug of hot chocolate ☕",
    "fruity smoothie with fresh berries 🍓",
    "classic cup of coffee ☕",
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
        await channel.send(f"🧸 Welcome to {SERVER_NAME}, {member.mention} !! {msg}")

# When someone leaves
@bot.event
async def on_member_remove(member):
    channel = member.guild.system_channel
    if channel:
        msg = random.choice(gone_messages)
        await channel.send(f"🧸 {member.name} left… {msg}")


today = None
def get_bot_mood():
    global today

    today = datetime.now().strftime("%Y-%m-%d")

    # Seed random with today's date
    random.seed(today+"mood")

    mystery = random.choice(mysteries)

    moods = [
        "sleepy. Button is taking a nap. She encourages you to rest too...🌙",
        "calm. Button is going to grab a cup of tea and read a book, you could join her too.🫖",
        "happy. The world is a wonderful place! Join Button in taking a walk in the park! 🌸",
        "playful. Button is going to play some games! Would you like to join her? 🧸",
        "a bit down. Sadness is a normal feeling and it's okay to feel that way sometimes. We can always be here for those we love, though. Would you like to offer her some comfort? 🤍",
        f"thinking. Button is pondering the mysteries of the universe. {mystery} 🤔",
        "cozy. Button is snuggled up in the sofa, watching her favorite movie. You're invited to join her; the more the merrier! 🛋️ "
    ]

    return random.choice(moods)


@bot.command()
async def mood(ctx):
    mood = get_bot_mood()   
    await ctx.send(f"🧸 Today, Button feels {mood}")

# Command to get encouragement
@bot.command()
async def hug(ctx, member: discord.Member = None):
    msg = random.choice(encouragements)

    if member:
        await ctx.send(f"🧸 {ctx.author.mention} hugs {member.mention}! {msg}")
    else:
        adjective = random.choice(adjectives)
        await ctx.send(f"🧸 Button is giving you a {adjective} hug, {ctx.author.mention}! {msg}")

@bot.command()
async def goodnight(ctx, member: discord.Member = None):
    dream = random.choice(dreams)
    goodnight_messages = [
        f"Sleep well and dream of {dream}! 🌙🧸",
        "Sweet dreams! May your night be filled with warmth and comfort! 🌙💖",
        "Rest well! Tomorrow is a new day full of possibilities! 🌙✨",
        "Sleep tight! May your dreams be as soft and gentle as a teddy bear hug! 🌙🧸"
    ]
    msg = random.choice(goodnight_messages)
    if member:
        await ctx.send(f"🌙🧸 {ctx.author.mention} sends you a goodnight, {member.mention}! \n {msg} 💗")
    else:
        await ctx.send(f"🌙🧸 Goodnight {ctx.author.mention}! \n {msg} 💗")

@bot.command()
async def goodmorning(ctx, member: discord.Member = None):
    drink = random.choice(drinks)
    receiver = member.mention if member else ctx.author.mention
    greetings = [
        f"Good morning {receiver}!",
        f"Wakey wakey, {receiver}!",
        f"Rise and shine, {receiver}!"
    ]
    greeting = random.choice(greetings)
    goodmorning_messages = [
        f"{greeting} Rise and shine, it's a new day full of opportunities! ☀️🧸",
        f"{greeting} Time to start the day. Get a {drink} and enjoy the sunrise! ☀️💖",
        f"{greeting} May your day be filled with warmth, joy, and all things wonderful! ☀️✨",
        f"{greeting} Let's make today amazing together! ☀️🧸"
    ]
    msg = random.choice(goodmorning_messages)
    if member:
        await ctx.send(f"☀️🧸 {ctx.author.mention} sends you a goodmorning, {member.mention}! \n {msg} ")
    else:
        await ctx.send(f"☀️🧸 {msg} ")

@bot.command()
async def commands(ctx):
    commands_list = [
        "*mood - Check Button's mood for the day. Refreshes daily 💗",
        "*hug [@user] - Send a virtual hug to someone or receive one from Button 💗",
        "*goodmorning [@user] - Send a good morning message to someone or receive one from Button 💗",
        "*goodnight [@user] - Send a goodnight message to someone or receive one from Button 💗",
        "*commands - Display this list of commands."
    ]
    await ctx.send("🧸 Here are the available commands for Button:\n" + "\n".join(commands_list))
    
keep_alive()
bot.run(os.getenv("TOKEN"))