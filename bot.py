from datetime import datetime
from discord.ui import Button, View
import asyncio
from concurrent.futures import wait
import discord
from discord.ext import commands
from discord import Interaction
import random
import os
import json
from keep_alive import keep_alive
from datetime import datetime
import re

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="*", intents=intents)

server_id = int(os.getenv("SERVER_ID"))
SERVER_NAME = os.getenv("SERVER_NAME")

# User IDs
USERA = int(os.getenv("USERA"))
USERB = int(os.getenv("USERB"))
USERC = int(os.getenv("USERC"))
USERD = int(os.getenv("USERD"))
USERE = int(os.getenv("USERE"))

# Map user IDs to their JSON files
USER_BOOK_FILES = {
    USERA: "./userA_books_enriched.json",
    USERB: "./userB_books_enriched.json",
    USERC: "./userC_books_enriched.json",
    USERD: "./userD_books_enriched.json",
    USERE: "./userE_books_enriched.json",
}

# Cache for user books
user_books_cache = {}

class SimpleBookPaginationView(View):
    def __init__(self, ctx, books, page, items_per_page=10):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.books = books
        self.page = page
        self.items_per_page = items_per_page
        self.total_pages = (len(books) + items_per_page - 1) // items_per_page
        self.message = None
    
    async def interaction_check(self, interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("🧸 This isn't your list!", ephemeral=True)
            return False
        return True
    
    async def update_page(self, interaction, new_page):
        self.page = new_page
        
        start = (self.page - 1) * self.items_per_page
        end = min(start + self.items_per_page, len(self.books))
        
        book_list = []
        for i, book in enumerate(self.books[start:end], start=start+1):
            book_list.append(format_book_list(book, i))
        
        embed = discord.Embed(
            title=f"🧸📚 {self.ctx.author.display_name}'s To-Read Books (Page {self.page}/{self.total_pages})",
            description="\n".join(book_list) if book_list else "No books on this page.",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Total: {len(self.books)} books")
        
        # Update buttons (enable/disable based on current page)
        for child in self.children:
            if isinstance(child, Button):
                if child.custom_id == "prev":
                    child.disabled = (self.page == 1)
                elif child.custom_id == "next":
                    child.disabled = (self.page == self.total_pages)
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="◀️", style=discord.ButtonStyle.primary, custom_id="prev")
    async def prev_button(self, interaction: discord.Interaction, button: Button):
        if self.page > 1:
            await self.update_page(interaction, self.page - 1)
    
    @discord.ui.button(label="Page", style=discord.ButtonStyle.secondary, disabled=True, custom_id="page_indicator")
    async def page_indicator(self, interaction: discord.Interaction, button: Button):
        pass
    
    @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary, custom_id="next")
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.page < self.total_pages:
            await self.update_page(interaction, self.page + 1)

def split_long_text(text, max_length=1000):
    """Split long text into chunks for Discord embed fields"""
    if not text:
        return [text]
    
    # If text is shorter than max_length, return as is
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    # Split by sentences to avoid cutting in the middle of a word
    sentences = text.replace('\n', ' ').split('. ')
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 2 <= max_length:
            if current_chunk:
                current_chunk += ". " + sentence
            else:
                current_chunk = sentence
        else:
            if current_chunk:
                chunks.append(current_chunk + ".")
                current_chunk = sentence
            else:
                # If a single sentence is too long, split by words
                words = sentence.split()
                current_chunk = ""
                for word in words:
                    if len(current_chunk) + len(word) + 1 <= max_length:
                        if current_chunk:
                            current_chunk += " " + word
                        else:
                            current_chunk = word
                    else:
                        chunks.append(current_chunk + "...")
                        current_chunk = word
                chunks.append(current_chunk + ".")
                return chunks
    
    if current_chunk:
        chunks.append(current_chunk + ".")
    
    return chunks

def truncate_summary(summary, max_length=1000):
    """Truncate summary to a reasonable length for Discord embed"""
    if not summary:
        return "No summary available."
    
    # Clean up the summary
    summary = summary.strip()
    
    # If it's short enough, return as is
    if len(summary) <= max_length:
        return summary
    
    # Try to find a good cutoff point (end of a sentence)
    cutoff = summary[:max_length]
    last_period = cutoff.rfind('.')
    last_question = cutoff.rfind('?')
    last_exclamation = cutoff.rfind('!')
    
    # Use the last sentence ending as cutoff
    last_sentence_end = max(last_period, last_question, last_exclamation)
    
    if last_sentence_end > max_length - 50:
        return cutoff[:last_sentence_end + 1] + " ..."
    else:
        return cutoff + " ..."
    
def get_user_books(user_id):
    """Get books for a specific user from their JSON file"""
    if user_id in user_books_cache:
        return user_books_cache[user_id]
    
    filename = USER_BOOK_FILES.get(user_id)
    if not filename:
        return []
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            books = json.load(f)
            user_books_cache[user_id] = books
            return books
    except FileNotFoundError:
        print(f"{filename} not found!")
        return []
    except json.JSONDecodeError:
        print(f"Invalid JSON in {filename}!")
        return []

def save_user_books(user_id, books):
    """Save books for a specific user to their JSON file"""
    filename = USER_BOOK_FILES.get(user_id)
    if not filename:
        return False
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(books, f, indent=2, ensure_ascii=False)
        # Update cache
        user_books_cache[user_id] = books
        return True
    except Exception as e:
        print(f"Error saving books for user {user_id}: {e}")
        return False

def is_authorized_user(ctx, target_user_id=None):
    """Check if the command user is authorized to modify books"""
    user_id = ctx.author.id
    
    # If target_user_id is provided, check if the user is modifying their own list
    if target_user_id is not None:
        return user_id == target_user_id
    
    # Otherwise, check if the user has their own book list
    return user_id in USER_BOOK_FILES

def get_book_list_for_user(ctx):
    """Get the books for the user who sent the command"""
    user_id = ctx.author.id
    if not is_authorized_user(ctx):
        return None
    
    return get_user_books(user_id)

def find_book_by_title(books, query):
    """Find books matching a title query (case insensitive)"""
    query = query.lower()
    return [book for book in books if query in book['title'].lower()]

def get_book_length(pages):
    """Categorize book length based on page count"""
    if not pages or not pages.isdigit():
        return "📄 Unknown length"
    
    pages_int = int(pages)
    if pages_int < 300:
        return "📄 Short Read (< 300 pages)"
    elif pages_int < 500:
        return "📄 Medium Read (300-499 pages)"
    else:
        return "📄 Long Read (500+ pages)"

def get_length_emoji(pages):
    """Get an emoji representing book length"""
    if not pages or not pages.isdigit():
        return "📄"
    
    pages_int = int(pages)
    if pages_int < 300:
        return "📖"  # Short
    elif pages_int < 500:
        return "📚"  # Medium
    else:
        return "📕"  # Long

# Update the format_book_embed function
def format_book_embed(book, title_prefix="", user_id=None):
    """Format a book as a Discord embed with proper text handling"""
    embed = discord.Embed(
        title=f"{title_prefix}{book['title']}",
        color=discord.Color.blue()
    )
    
    # Author and basic info
    embed.add_field(name="✍️ Author", value=book['author'], inline=True)
    
    # Add page length with category
    if book.get('pages') and book['pages'].isdigit():
        length_category = get_book_length(book['pages'])
        embed.add_field(name="📄 Pages", value=f"{book['pages']} pages", inline=True)
        embed.add_field(name="📏 Length", value=length_category, inline=False)
    
    if book.get('series'):
        embed.add_field(name="🔗 Series", value=book['series'], inline=False)
    
    # Genres and moods
    genres = [tag.replace('genre: ', '') for tag in book.get('tags', []) if tag.startswith('genre:')]
    moods = [tag.replace('mood: ', '') for tag in book.get('tags', []) if tag.startswith('mood:')]
    
    if genres:
        embed.add_field(name="🎭 Genres", value=', '.join(genres), inline=False)
    if moods:
        embed.add_field(name="💭 Moods", value=', '.join(moods), inline=False)
    
    # Other tags
    other_tags = [tag for tag in book.get('tags', []) if not tag.startswith('genre:') and not tag.startswith('mood:')]
    if other_tags:
        embed.add_field(name="🏷️ Tags", value=', '.join(other_tags[:5]), inline=False)
    
    # Summary - properly truncated
    if book.get('summary'):
        summary = truncate_summary(book['summary'], 950)  # Leave room for "Read more" indicator
        embed.add_field(name="📝 Summary", value=summary, inline=False)
    
    # Add user info
    if user_id:
        user = bot.get_user(user_id)
        if user:
            embed.set_footer(text=f"📚 {user.display_name}'s Library")
    
    return embed

# Update format_book_list function
def format_book_list(book, index):
    """Format a book for list view with length indicator"""
    length_emoji = get_length_emoji(book.get('pages'))
    return f"`{index}.` {length_emoji} **{book['title']}** — *{book['author']}*" 

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
    "What is the sound of one hand clapping?",
    "Why is moonlight silver?",
    "What is the color of a shadow?",
    "Why is x always the unknown?",
    "What is the shape of a thought?",
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
    
    # Load books for all users
    try:
        for user_id in USER_BOOK_FILES:
            books = get_user_books(user_id)
            user = bot.get_user(user_id)
            if user:
                print(f"🧸📚 Loaded {len(books)} books for {user.display_name}")
            else:
                print(f"🧸📚 Loaded {len(books)} books for user {user_id}")
    except Exception as e:
        print(f"Error loading books: {e}")
    
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
async def mystery(ctx):
    mystery = random.choice(mysteries)
    await ctx.send(f"🧸 The mystery of the day is: {mystery}")

@bot.command()
async def dream(ctx):
    dream = random.choice(dreams)
    await ctx.send(f"🧸 Button's dreaming of {dream}")

@bot.command()
async def drink(ctx):
    drink = random.choice(drinks)
    await ctx.send(f"🧸 Button is enjoying a {drink}")

@bot.command()
async def birthday(ctx, member: discord.Member = None):
    if member:
        user_id = member.id
        if user_id in birthdays:
            day, month = birthdays[user_id]
            await ctx.send(f"🧸 {member.mention}'s birthday is on {day}/{month} 🎉")
        else:
            await ctx.send(f"🧸 Sorry, I don't have {member.mention}'s birthday information. 💔")
    else:
        await ctx.send("🧸 Please mention a user to check their birthday. 💗")

@bot.command()
async def add_birthday(ctx, member: discord.Member, date: str):
    if ctx.author.guild_permissions.administrator:
        try:
            day, month = map(int, date.split("/"))
            if 1 <= day <= 31 and 1 <= month <= 12:
                birthdays[member.id] = (day, month)
                await ctx.send(f"🧸 Birthday for {member.mention} has been set to {day}/{month} 🎉")
            else:
                await ctx.send("🧸 Invalid date format. Please use DD/MM format. 💔")
        except ValueError:
            await ctx.send("🧸 Invalid date format. Please use DD/MM format. 💔")
    else:
        await ctx.send("🧸 You do not have permission to add birthdays. 💔")

@bot.command()
async def remove_birthday(ctx, member: discord.Member):
    if ctx.author.guild_permissions.administrator:
        if member.id in birthdays:
            del birthdays[member.id]
            await ctx.send(f"🧸 Birthday for {member.mention} has been removed. 💔")
        else:
            await ctx.send(f"🧸 No birthday information found for {member.mention}. 💔")
    else:
        await ctx.send("🧸 You do not have permission to remove birthdays. 💔")

@bot.command()
async def edit_birthday(ctx, member: discord.Member, date: str):
    if ctx.author.guild_permissions.administrator:
        try:
            day, month = map(int, date.split("/"))
            if 1 <= day <= 31 and 1 <= month <= 12:
                birthdays[member.id] = (day, month)
                await ctx.send(f"🧸 Birthday for {member.mention} has been updated to {day}/{month} 🎉")
            else:
                await ctx.send("🧸 Invalid date format. Please use DD/MM format. 💔")
        except ValueError:
            await ctx.send("🧸 Invalid date format. Please use DD/MM format. 💔")
    else:
        await ctx.send("🧸 You do not have permission to edit birthdays. 💔")

@bot.command()
async def list_birthdays(ctx):
    if birthdays:
        birthday_list = []
        for user_id, (day, month) in birthdays.items():
            user = await bot.fetch_user(user_id)
            birthday_list.append(f"{user.name}: {day}/{month}")
        await ctx.send("🧸 Here are the birthdays I know about:\n" + "\n".join(birthday_list))
    else:
        await ctx.send("🧸 I don't have any birthday information yet. 💔")

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
async def mybooks(ctx):
    """Check if you have a book list set up"""
    user_id = ctx.author.id
    
    if user_id in USER_BOOK_FILES:
        books = get_user_books(user_id)
        await ctx.send(f"🧸📚 {ctx.author.mention}, you have {len(books)} books in your to-read list! ")
    else:
        await ctx.send(f"🧸📚 {ctx.author.mention}, you don't have a book list set up yet. Please contact an admin. ")

@bot.command()
async def recommend(ctx):
    """Recommend a random book from YOUR to-read list"""
    books = get_book_list_for_user(ctx)
    if books is None:
        await ctx.send("🧸📚 You don't have a book list set up yet! 💔")
        return
    
    if not books:
        await ctx.send("🧸📚 *sniff sniff* Button can't find any books in your to-read list! 💔")
        return
    
    book = random.choice(books)
    embed = format_book_embed(book, "🧸📚 Button has thought very hard about this and she recommends: ", ctx.author.id)
    embed.set_footer(text=f"Book #{books.index(book) + 1} of {len(books)} in your list")
    await ctx.send(embed=embed)

@bot.command(aliases=['list'])
async def list_books(ctx, page: int = 1):
    """List YOUR books alphabetically (numbered) with interactive pagination"""
    books = get_book_list_for_user(ctx)
    if books is None:
        await ctx.send("🧸📚 You don't have a book list set up yet! 💔")
        return
    
    if not books:
        await ctx.send("🧸📚 Button can't find any books in your to-read list! 💔")
        return
    
    # Sort alphabetically by title
    sorted_books = sorted(books, key=lambda x: x['title'].lower())
    
    # Pagination: 10 books per page
    items_per_page = 10
    total_pages = (len(sorted_books) + items_per_page - 1) // items_per_page
    
    if page < 1 or page > total_pages:
        await ctx.send(f"🧸📚 That page doesn't exist! There are {total_pages} pages. 💔")
        return
    
    start = (page - 1) * items_per_page
    end = min(start + items_per_page, len(sorted_books))
    
    # Create the list
    book_list = []
    for i, book in enumerate(sorted_books[start:end], start=start+1):
        book_list.append(format_book_list(book, i))
    
    embed = discord.Embed(
        title=f"🧸📚 {ctx.author.display_name}'s To-Read Books (Page {page}/{total_pages})",
        description="\n".join(book_list) if book_list else "No books on this page.",
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Total: {len(books)} books")
    
    # Create the pagination view
    view = SimpleBookPaginationView(ctx, sorted_books, page, items_per_page)
    
    # Send the message and store it in the view
    message = await ctx.send(embed=embed, view=view)
    view.message = message

@bot.command(aliases=['find', 'lookup'])
async def search_book(ctx, *, query):
    """Search for a book in YOUR list by title"""
    if not query:
        await ctx.send("🧸📚 Please provide a title to search for. 💔")
        return
    books = get_book_list_for_user(ctx)
    if books is None:
        await ctx.send("🧸📚 You don't have a book list set up yet! 💔")
        return
    
    results = find_book_by_title(books, query)
    
    if not results:
        await ctx.send(f"🧸📚 Button couldn't find a book matching '{query}' in your list. 💔")
        return
    
    if len(results) == 1:
        embed = format_book_embed(results[0], "📖 Book Details: ", ctx.author.id)
        await ctx.send(embed=embed)
    else:
        # Multiple results found
        book_list = []
        for i, book in enumerate(results[:10], 1):
            book_list.append(format_book_list(book, i))
        
        embed = discord.Embed(
            title=f"🔍 🧸Found {len(results)} books matching '{query}'",
            description="\n".join(book_list),
            color=discord.Color.blue()
        )
        embed.set_footer(text="Use *book_info 'exact title' for full details")
        await ctx.send(embed=embed)

@bot.command()
async def book_info(ctx, *, title: str):
    """Get ALL information about a book including the full summary.
    Usage: *book_info Book Title"""
    
    if not title:
        await ctx.send("🧸📚 Please provide a book title. 💔")
        return

    user_id = ctx.author.id
    books = get_book_list_for_user(ctx)
    
    if books is None:
        await ctx.send("🧸📚 You don't have a book list set up yet! 💔")
        return
    
    results = [b for b in books if b['title'].lower() == title.lower()]
    
    if not results:
        await ctx.send(f"🧸📚 Couldn't find '{title}' in your list. 💔")
        return
    
    book = results[0]
    
    # First, send the basic embed with truncated summary
    embed = format_book_embed(book, "📖 Full Book Info: ", ctx.author.id)
    await ctx.send(embed=embed)
    
    # If there's a summary, send the full version separately
    if book.get('summary') and len(book['summary']) > 950:
        await ctx.send("📝 **Full Summary:**")
        summary_chunks = split_long_text(book['summary'], 950)
        
        for i, chunk in enumerate(summary_chunks, start=1):
            if len(summary_chunks) == 1:
                await ctx.send(chunk)
            else:
                await ctx.send(f"**Part {i}/{len(summary_chunks)}:**\n{chunk}")

@bot.command()
async def add_book(ctx, *, args: str):
    """Add a book to YOUR to-read list.
    Usage: *add_book Title | Author | Pages | Series
    Example: *add_book The Hobbit | J.R.R. Tolkien | 310 | Middle Earth
    Only Title is required, everything else is optional."""
    
    if not args:
        await ctx.send("🧸📚 Please provide book details. Usage: *add_book Title | Author | Pages | Series 💔")
        return

    user_id = ctx.author.id
    
    if user_id not in USER_BOOK_FILES:
        await ctx.send("🧸📚 You don't have a book list set up yet! Please contact an admin. 💔")
        return
    
    books = get_user_books(user_id)
    
    # Split by the delimiter |
    parts = [p.strip() for p in args.split('|')]
    
    # First part is always the title
    title = parts[0] if parts else None
    
    if not title:
        await ctx.send("🧸📚 You need to at least provide a title! Usage: *add_book Title | Author | Pages | Series 💔")
        return
    
    # Check if book already exists
    existing = [b for b in books if b['title'].lower() == title.lower()]
    if existing:
        await ctx.send(f"🧸📚 '{title}' is already in your list! 💔")
        return
    
    # Get optional fields
    author = parts[1] if len(parts) > 1 and parts[1] else "Unknown"
    pages = parts[2] if len(parts) > 2 and parts[2] else ""
    series = parts[3] if len(parts) > 3 and parts[3] else None
    
    # Create new book entry
    new_book = {
        "title": title,
        "series": series,
        "author": author,
        "pages": pages,
        "tags": [],
        "summary": ""
    }
    
    books.append(new_book)
    if save_user_books(user_id, books):
        await ctx.send(f"🧸📚 Added '{title}' by {author} to your to-read list! 📖")
        if pages:
            await ctx.send(f"📄 Pages: {pages}")
        if series:
            await ctx.send(f"🔗 Series: {series}")
    else:
        await ctx.send("❌ Failed to save the book. Please check the file permissions. 💔")

@bot.command()
async def remove_book(ctx, *, title: str):
    """Remove a book from YOUR to-read list.
    Usage: *remove_book Title
    Example: *remove_book The Hobbit"""
    
    if not title:
        await ctx.send("🧸📚 Please provide a book title to remove. 💔")
        return

    user_id = ctx.author.id
    books = get_book_list_for_user(ctx)
    
    if books is None:
        await ctx.send("🧸📚 You don't have a book list set up yet! 💔")
        return
    
    # Find exact title match
    matches = [b for b in books if b['title'].lower() == title.lower()]
    
    if not matches:
        # If no exact match, try partial match
        partial_matches = [b for b in books if title.lower() in b['title'].lower()]
        if partial_matches:
            # Show matching books
            book_list = []
            for i, book in enumerate(partial_matches[:5], 1):
                book_list.append(f"{i}. {book['title']} — {book['author']}")
            
            await ctx.send(f"🧸📚 Multiple books found matching '{title}'. Please use the exact title:\n" + "\n".join(book_list))
            return
        else:
            await ctx.send(f"🧸📚 Couldn't find '{title}' in your list. 💔")
            return
    
    # Remove the book
    book_to_remove = matches[0]
    books.remove(book_to_remove)
    
    if save_user_books(user_id, books):
        await ctx.send(f"🗑️ Removed '{book_to_remove['title']}' from your to-read list. 🧸💔")
    else:
        await ctx.send("❌ Failed to remove the book. Please check the file permissions. 💔")

@bot.command()
async def edit_book(ctx, *, args: str):
    """Edit a book in YOUR list.
    Usage: *edit_book Old Title | field | new value
    Fields: title, author, pages, series, summary, genre, mood, tags
    
    Examples:
    *edit_book The Hobbit | title | The Hobbit: An Unexpected Journey
    *edit_book The Hobbit | author | J.R.R. Tolkien
    *edit_book The Hobbit | pages | 310
    *edit_book The Hobbit | series | Middle Earth
    *edit_book The Hobbit | genre | Fantasy, Adventure
    *edit_book The Hobbit | mood | Adventurous, Whimsical"""
    
    if not args:
        await ctx.send("🧸📚 Please provide book details. Usage: *edit_book Old Title | field | new value 💔")
        return

    user_id = ctx.author.id
    books = get_book_list_for_user(ctx)
    
    if books is None:
        await ctx.send("🧸📚 You don't have a book list set up yet! 💔")
        return
    
    # Split by the delimiter |
    parts = [p.strip() for p in args.split('|')]
    
    if len(parts) < 2:
        await ctx.send("🧸📚 Invalid format! Use: *edit_book Old Title | field | new value 💔")
        return
    
    old_title = parts[0]
    field = parts[1].lower() if len(parts) > 1 else None
    new_value = parts[2] if len(parts) > 2 else None
    
    # Find the book
    matches = [b for b in books if b['title'].lower() == old_title.lower()]
    
    if not matches:
        await ctx.send(f"🧸📚 Couldn't find '{old_title}' in your list. 💔")
        return
    
    book = matches[0]
    
    # If no field specified, show help
    if field is None or field == "help":
        embed = discord.Embed(
            title=f"✏️ Editing: {book['title']}",
            description="**Current Information:**",
            color=discord.Color.blue()
        )
        embed.add_field(name="Title", value=book['title'], inline=False)
        embed.add_field(name="Author", value=book['author'], inline=False)
        embed.add_field(name="Pages", value=book.get('pages', 'Not set'), inline=False)
        embed.add_field(name="Series", value=book.get('series', 'Not set'), inline=False)
        embed.add_field(name="Summary", value=book.get('summary', 'Not set')[:200] + "..." if book.get('summary') else 'Not set', inline=False)
        
        genres = [tag.replace('genre: ', '') for tag in book.get('tags', []) if tag.startswith('genre:')]
        moods = [tag.replace('mood: ', '') for tag in book.get('tags', []) if tag.startswith('mood:')]
        embed.add_field(name="Genres", value=', '.join(genres) if genres else 'Not set', inline=False)
        embed.add_field(name="Moods", value=', '.join(moods) if moods else 'Not set', inline=False)
        
        embed.add_field(
            name="📝 How to edit",
            value="`*edit_book Old Title | title | New Title`\n"
                  "`*edit_book Old Title | author | New Author`\n"
                  "`*edit_book Old Title | pages | 123`\n"
                  "`*edit_book Old Title | series | Series Name`\n"
                  "`*edit_book Old Title | summary | New summary text`\n"
                  "`*edit_book Old Title | genre | Fantasy, Sci-Fi` (comma-separated)\n"
                  "`*edit_book Old Title | mood | Dark, Suspenseful` (comma-separated)\n"
                  "`*edit_book Old Title | tags | custom, tags`",
            inline=False
        )
        await ctx.send(embed=embed)
        return
    
    old_value = None
    
    # Handle different fields
    if field == "title":
        old_value = book['title']
        # Check if new title already exists
        existing = [b for b in books if b['title'].lower() == new_value.lower() and b != book]
        if existing:
            await ctx.send(f"🧸📚 '{new_value}' already exists in your list! 💔")
            return
        book['title'] = new_value
        await ctx.send(f"✏️ Updated title from '{old_value}' to '{new_value}'! 🧸✨")
        
    elif field == "author":
        old_value = book['author']
        book['author'] = new_value
        await ctx.send(f"✏️ Updated author of '{book['title']}' from '{old_value}' to '{new_value}'! 🧸✨")
        
    elif field == "pages":
        old_value = book.get('pages', 'Not set')
        if new_value and not new_value.isdigit():
            await ctx.send("❌ Pages must be a number! 🧸")
            return
        book['pages'] = new_value
        await ctx.send(f"✏️ Updated pages of '{book['title']}' from '{old_value}' to '{new_value}'! 🧸✨")
        
    elif field == "series":
        old_value = book.get('series', 'Not set')
        book['series'] = new_value if new_value else None
        await ctx.send(f"✏️ Updated series of '{book['title']}' from '{old_value}' to '{new_value}'! 🧸✨")
        
    elif field == "summary":
        old_value = book.get('summary', 'Not set')[:50] + "..." if book.get('summary') else 'Not set'
        book['summary'] = new_value
        await ctx.send(f"✏️ Updated summary of '{book['title']}'! 🧸✨")
        
    elif field == "genre" or field == "genres":
        # Handle multiple genres
        genres = [g.strip() for g in new_value.split(',')]
        # Remove old genre tags
        book['tags'] = [tag for tag in book.get('tags', []) if not tag.startswith('genre:')]
        # Add new genre tags
        for genre in genres:
            if genre:
                book['tags'].append(f"genre: {genre}")
        await ctx.send(f"✏️ Updated genres of '{book['title']}' to: {', '.join(genres)}! 🧸✨")
        
    elif field == "mood" or field == "moods":
        # Handle multiple moods
        moods = [m.strip() for m in new_value.split(',')]
        # Remove old mood tags
        book['tags'] = [tag for tag in book.get('tags', []) if not tag.startswith('mood:')]
        # Add new mood tags
        for mood in moods:
            if mood:
                book['tags'].append(f"mood: {mood}")
        await ctx.send(f"✏️ Updated moods of '{book['title']}' to: {', '.join(moods)}! 🧸✨")
        
    elif field == "tags":
        # Add custom tags
        new_tags = [t.strip() for t in new_value.split(',')]
        # Remove old non-genre/non-mood tags
        book['tags'] = [tag for tag in book.get('tags', []) if tag.startswith('genre:') or tag.startswith('mood:')]
        # Add new tags
        for tag in new_tags:
            if tag and not tag.startswith('genre:') and not tag.startswith('mood:'):
                book['tags'].append(tag)
        await ctx.send(f"✏️ Updated tags of '{book['title']}'! 🧸✨")
        
    else:
        await ctx.send(f"❌ Unknown field '{field}'. Available fields: title, author, pages, series, summary, genre, mood, tags 🧸")
        return
    
    # Save changes
    if save_user_books(user_id, books):
        await ctx.send("💾 Changes saved successfully! 🧸")
    else:
        await ctx.send("❌ Failed to save changes. Please check file permissions. 💔")

@bot.command()
async def add_genre(ctx, *, args: str):
    """Add a genre to a book.
    Usage: *add_genre Book Title | Genre
    Example: *add_genre The Hobbit | Fantasy"""
    
    if not args:
        await ctx.send("🧸📚 Please provide book details. Usage: *add_genre Book Title | Genre 💔")
        return

    user_id = ctx.author.id
    books = get_book_list_for_user(ctx)
    
    if books is None:
        await ctx.send("🧸📚 You don't have a book list set up yet! 💔")
        return
    
    parts = [p.strip() for p in args.split('|')]
    
    if len(parts) < 2:
        await ctx.send("🧸📚 Invalid format! Use: *add_genre Book Title | Genre 💔")
        return
    
    title = parts[0]
    genre = parts[1]
    
    matches = [b for b in books if b['title'].lower() == title.lower()]
    if not matches:
        await ctx.send(f"🧸📚 Couldn't find '{title}' in your list. 💔")
        return
    
    book = matches[0]
    genre = genre.replace('genre: ', '').strip()
    existing_genres = [tag for tag in book.get('tags', []) if tag.startswith('genre:')]
    if f"genre: {genre}" in existing_genres:
        await ctx.send(f"🎭 '{genre}' is already a genre for this book! 🧸")
        return
    
    book['tags'].append(f"genre: {genre}")
    if save_user_books(user_id, books):
        await ctx.send(f"🎭 Added genre '{genre}' to '{book['title']}'! 🧸✨")
    else:
        await ctx.send("❌ Failed to save changes. 💔")

@bot.command()
async def remove_genre(ctx, *, args: str):
    """Remove a genre from a book.
    Usage: *remove_genre Book Title | Genre
    Example: *remove_genre The Hobbit | Fantasy"""
    
    if not args:
        await ctx.send("🧸📚 Please provide book details. Usage: *remove_genre Book Title | Genre 💔")
        return

    user_id = ctx.author.id
    books = get_book_list_for_user(ctx)
    
    if books is None:
        await ctx.send("🧸📚 You don't have a book list set up yet! 💔")
        return
    
    parts = [p.strip() for p in args.split('|')]
    
    if len(parts) < 2:
        await ctx.send("🧸📚 Invalid format! Use: *remove_genre Book Title | Genre 💔")
        return
    
    title = parts[0]
    genre = parts[1]
    
    matches = [b for b in books if b['title'].lower() == title.lower()]
    if not matches:
        await ctx.send(f"🧸📚 Couldn't find '{title}' in your list. 💔")
        return
    
    book = matches[0]
    genre = genre.replace('genre: ', '').strip()
    genre_tag = f"genre: {genre}"
    
    if genre_tag not in book['tags']:
        await ctx.send(f"🎭 '{genre}' is not a genre for this book! 🧸")
        return
    
    book['tags'].remove(genre_tag)
    if save_user_books(user_id, books):
        await ctx.send(f"🗑️ Removed genre '{genre}' from '{book['title']}'! 🧸")
    else:
        await ctx.send("❌ Failed to save changes. 💔")

@bot.command()
async def add_mood(ctx, *, args: str):
    """Add a mood to a book.
    Usage: *add_mood Book Title | Mood
    Example: *add_mood The Hobbit | Adventurous"""
    
    if not args:
        await ctx.send("🧸📚 Please provide book details. Usage: *add_mood Book Title | Mood 💔")
        return

    user_id = ctx.author.id
    books = get_book_list_for_user(ctx)
    
    if books is None:
        await ctx.send("🧸📚 You don't have a book list set up yet! 💔")
        return
    
    parts = [p.strip() for p in args.split('|')]
    
    if len(parts) < 2:
        await ctx.send("🧸📚 Invalid format! Use: *add_mood Book Title | Mood 💔")
        return
    
    title = parts[0]
    mood = parts[1]
    
    matches = [b for b in books if b['title'].lower() == title.lower()]
    if not matches:
        await ctx.send(f"🧸📚 Couldn't find '{title}' in your list. 💔")
        return
    
    book = matches[0]
    mood = mood.replace('mood: ', '').strip()
    existing_moods = [tag for tag in book.get('tags', []) if tag.startswith('mood:')]
    if f"mood: {mood}" in existing_moods:
        await ctx.send(f"💭 '{mood}' is already a mood for this book! 🧸")
        return
    
    book['tags'].append(f"mood: {mood}")
    if save_user_books(user_id, books):
        await ctx.send(f"💭 Added mood '{mood}' to '{book['title']}'! 🧸✨")
    else:
        await ctx.send("❌ Failed to save changes. 💔")

@bot.command()
async def remove_mood(ctx, *, args: str):
    """Remove a mood from a book.
    Usage: *remove_mood Book Title | Mood
    Example: *remove_mood The Hobbit | Adventurous"""
    
    if not args:
        await ctx.send("🧸📚 Please provide book details. Usage: *remove_mood Book Title | Mood 💔")
        return

    user_id = ctx.author.id
    books = get_book_list_for_user(ctx)
    
    if books is None:
        await ctx.send("🧸📚 You don't have a book list set up yet! 💔")
        return
    
    parts = [p.strip() for p in args.split('|')]
    
    if len(parts) < 2:
        await ctx.send("🧸📚 Invalid format! Use: *remove_mood Book Title | Mood 💔")
        return
    
    title = parts[0]
    mood = parts[1]
    
    matches = [b for b in books if b['title'].lower() == title.lower()]
    if not matches:
        await ctx.send(f"🧸📚 Couldn't find '{title}' in your list. 💔")
        return
    
    book = matches[0]
    mood = mood.replace('mood: ', '').strip()
    mood_tag = f"mood: {mood}"
    
    if mood_tag not in book['tags']:
        await ctx.send(f"💭 '{mood}' is not a mood for this book! 🧸")
        return
    
    book['tags'].remove(mood_tag)
    if save_user_books(user_id, books):
        await ctx.send(f"🗑️ Removed mood '{mood}' from '{book['title']}'! 🧸")
    else:
        await ctx.send("❌ Failed to save changes. 💔")

@bot.command(aliases=['bookstats'])
async def library_stats(ctx):
    """Get statistics about YOUR to-read library"""
    books = get_book_list_for_user(ctx)
    if books is None:
        await ctx.send("🧸📚 You don't have a book list set up yet! 💔")
        return
    
    if not books:
        await ctx.send("🧸📚 Button can't find any books in your to-read list! 💔")
        return
    
    total = len(books)
    with_summary = sum(1 for b in books if b.get('summary'))
    with_genres = sum(1 for b in books if any('genre:' in tag for tag in b.get('tags', [])))
    with_moods = sum(1 for b in books if any('mood:' in tag for tag in b.get('tags', [])))
    
    # Count genre distribution
    genre_counts = {}
    for book in books:
        genres = [tag.replace('genre: ', '') for tag in book.get('tags', []) if tag.startswith('genre:')]
        for genre in genres:
            genre_counts[genre] = genre_counts.get(genre, 0) + 1
    
    # Get top 5 genres
    top_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    embed = discord.Embed(
        title=f"📊 {ctx.author.display_name}'s Book Library Stats",
        color=discord.Color.gold()
    )
    
    embed.add_field(name="📚 Total Books", value=str(total), inline=True)
    embed.add_field(name="📝 With Summaries", value=f"{with_summary}/{total}", inline=True)
    embed.add_field(name="🎭 With Genres", value=f"{with_genres}/{total}", inline=True)
    embed.add_field(name="💭 With Moods", value=f"{with_moods}/{total}", inline=True)
    
    if top_genres:
        genre_text = "\n".join([f"• {genre}: {count}" for genre, count in top_genres])
        embed.add_field(name="🎭 Top Genres", value=genre_text, inline=False)
    
    embed.set_footer(text="Button loves helping you find your next read! 🧸")
    
    await ctx.send(embed=embed)

@bot.command()
async def summary(ctx, *, title: str):
    """Get the full summary of a specific book without truncation.
    Usage: *summary Book Title"""
    if not title:
        await ctx.send("🧸📚 Please provide a book title. 💔")
        return
    user_id = ctx.author.id
    books = get_book_list_for_user(ctx)
    
    if books is None:
        await ctx.send("🧸📚 You don't have a book list set up yet! 💔")
        return
    
    results = [b for b in books if b['title'].lower() == title.lower()]
    
    if not results:
        await ctx.send(f"🧸📚 Couldn't find '{title}' in your list. 💔")
        return
    
    book = results[0]
    
    if not book.get('summary'):
        await ctx.send(f"📝 No summary available for '{book['title']}'. 🧸")
        return
    
    # Split the summary into chunks of max 1000 characters
    summary_chunks = split_long_text(book['summary'], 950)
    
    # Send the first chunk with book info
    embed = discord.Embed(
        title=f"📝 Full Summary: {book['title']}",
        description=f"**Author:** {book['author']}",
        color=discord.Color.blue()
    )
    
    if len(summary_chunks) == 1:
        embed.add_field(name="Summary", value=summary_chunks[0], inline=False)
        await ctx.send(embed=embed)
    else:
        # Send the first chunk as an embed
        embed.add_field(name=f"Summary (Part 1/{len(summary_chunks)})", value=summary_chunks[0], inline=False)
        await ctx.send(embed=embed)
        
        # Send the rest as separate messages
        for i, chunk in enumerate(summary_chunks[1:], start=2):
            await ctx.send(f"**Part {i}/{len(summary_chunks)}:**\n{chunk}")

@bot.command()
async def recommendmood(ctx, *, mood):
    """Recommend a book from YOUR list by mood (e.g., *recommend_by_mood dark)"""
    if not mood:
        await ctx.send("🧸📚 Please specify a mood. 💔")
        return
    books = get_book_list_for_user(ctx)
    if books is None:
        await ctx.send("🧸📚 You don't have a book list set up yet! 💔")
        return
    
    mood = mood.lower()
    matches = []
    for book in books:
        moods = [tag.replace('mood: ', '').lower() for tag in book.get('tags', []) if tag.startswith('mood:')]
        if any(mood in m for m in moods):
            matches.append(book)
    
    if not matches:
        await ctx.send(f"💭 Button couldn't find any books with mood '{mood}'. Try *list_moods to see all available moods. 🧸")
        return
    
    book = random.choice(matches)
    embed = format_book_embed(book, f"💭 Button recommends (mood: {mood}): ", ctx.author.id)
    await ctx.send(embed=embed)

@bot.command()
async def recommendgenre(ctx, *, genre):
    """Recommend a book from YOUR list by genre (e.g., *recommend_by_genre fantasy)"""
    if not genre:
        await ctx.send("🧸📚 Please specify a genre. 💔")
        return
    books = get_book_list_for_user(ctx)
    if books is None:
        await ctx.send("🧸📚 You don't have a book list set up yet! 💔")
        return
    
    genre = genre.lower()
    matches = []
    for book in books:
        genres = [tag.replace('genre: ', '').lower() for tag in book.get('tags', []) if tag.startswith('genre:')]
        if any(genre in g for g in genres):
            matches.append(book)
    
    if not matches:
        await ctx.send(f"🎭 Button couldn't find any books with genre '{genre}'. Try *list_genres to see all available genres. 🧸")
        return
    
    book = random.choice(matches)
    embed = format_book_embed(book, f"🎭 Button recommends (genre: {genre}): ", ctx.author.id)
    await ctx.send(embed=embed)

@bot.command()
async def list_genres(ctx):
    """List all genres in YOUR library"""
    books = get_book_list_for_user(ctx)
    if books is None:
        await ctx.send("🧸📚 You don't have a book list set up yet! 💔")
        return
    
    genres = set()
    for book in books:
        for tag in book.get('tags', []):
            if tag.startswith('genre:'):
                genres.add(tag.replace('genre: ', ''))
    
    if not genres:
        await ctx.send("🎭 No genres found in your library. Try enriching your books first! 🧸")
        return
    
    genres_list = sorted(genres)
    embed = discord.Embed(
        title=f"🎭 {ctx.author.display_name}'s Available Genres ({len(genres_list)})",
        description=", ".join(genres_list),
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.command()
async def list_moods(ctx):
    """List all moods in YOUR library"""
    books = get_book_list_for_user(ctx)
    if books is None:
        await ctx.send("🧸📚 You don't have a book list set up yet! 💔")
        return
    
    moods = set()
    for book in books:
        for tag in book.get('tags', []):
            if tag.startswith('mood:'):
                moods.add(tag.replace('mood: ', ''))
    
    if not moods:
        await ctx.send("💭 No moods found in your library. Try enriching your books first! 🧸")
        return
    
    moods_list = sorted(moods)
    embed = discord.Embed(
        title=f"💭 {ctx.author.display_name}'s Available Moods ({len(moods_list)})",
        description=", ".join(moods_list),
        color=discord.Color.purple()
    )
    await ctx.send(embed=embed)

@bot.command()
async def refresh_books(ctx):
    """Refresh YOUR book list from the JSON file"""
    user_id = ctx.author.id
    
    if user_id not in USER_BOOK_FILES:
        await ctx.send("🧸📚 You don't have a book list set up yet! 💔")
        return
    
    # Clear cache for this user
    if user_id in user_books_cache:
        del user_books_cache[user_id]
    
    # Reload books
    books = get_user_books(user_id)
    await ctx.send(f"🔄 Refreshed! Loaded {len(books)} books from your to-read list. 🧸")

@bot.command()
async def recommendlength(ctx, length: str):
    """Recommend a book by length (short, medium, long)
    Example: *recommend_by_length short"""
    if not length:
        await ctx.send("🧸📚 Please specify a length: short, medium, or long. 🧸")
        return
    
    books = get_book_list_for_user(ctx)
    if books is None:
        await ctx.send("🧸📚 You don't have a book list set up yet! 🧸💔")
        return
    
    length = length.lower()
    
    # Define length ranges
    if length in ['short', 's']:
        matches = [b for b in books if b.get('pages') and b['pages'].isdigit() and int(b['pages']) < 300]
        length_display = "Short (< 300 pages)"
    elif length in ['medium', 'med', 'm']:
        matches = [b for b in books if b.get('pages') and b['pages'].isdigit() and 300 <= int(b['pages']) < 500]
        length_display = "Medium (300-499 pages)"
    elif length in ['long', 'l']:
        matches = [b for b in books if b.get('pages') and b['pages'].isdigit() and int(b['pages']) >= 500]
        length_display = "Long (500+ pages)"
    else:
        await ctx.send(f"🧸📚 Invalid length option. Use: short, medium, or long 🧸")
        return
    
    if not matches:
        await ctx.send(f"🧸📚 Button couldn't find any {length_display} books in your list! 🧸💔")
        return
    
    book = random.choice(matches)
    embed = format_book_embed(book, f"🧸📚 Button recommends ({length_display}): ", ctx.author.id)
    await ctx.send(embed=embed)

@bot.command()
async def list_length(ctx, length: str):
    """List all books of a specific length (short, medium, long)
    Example: *list_by_length short"""
    
    if not length:
        await ctx.send("🧸📚 Please specify a length: short, medium, or long 🧸")
        return
    
    books = get_book_list_for_user(ctx)
    if books is None:
        await ctx.send("🧸📚 You don't have a book list set up yet! 🧸💔")
        return
    
    length = length.lower()
    
    # Define length ranges
    if length in ['short', 's']:
        matches = sorted(
            [b for b in books if b.get('pages') and b['pages'].isdigit() and int(b['pages']) < 300],
            key=lambda x: x['title'].lower()
        )
        length_display = "Short (< 300 pages)"
    elif length in ['medium', 'med', 'm']:
        matches = sorted(
            [b for b in books if b.get('pages') and b['pages'].isdigit() and 300 <= int(b['pages']) < 500],
            key=lambda x: x['title'].lower()
        )
        length_display = "Medium (300-499 pages)"
    elif length in ['long', 'l']:
        matches = sorted(
            [b for b in books if b.get('pages') and b['pages'].isdigit() and int(b['pages']) >= 500],
            key=lambda x: x['title'].lower()
        )
        length_display = "Long (500+ pages)"
    else:
        await ctx.send(f"🧸📚 Invalid length option. Use: short, medium, or long 🧸")
        return
    
    if not matches:
        await ctx.send(f"🧸📚 Button couldn't find any {length_display} books in your list! 🧸💔")
        return
    
    # Pagination
    items_per_page = 10
    total_pages = (len(matches) + items_per_page - 1) // items_per_page
    page = 1
    
    # We'll just show the first page, but could add pagination
    start = 0
    end = min(items_per_page, len(matches))
    
    book_list = []
    for i, book in enumerate(matches[start:end], start=1):
        length_emoji = get_length_emoji(book.get('pages'))
        book_list.append(f"`{i}.` {length_emoji} **{book['title']}** — *{book['author']}* ({book.get('pages', '?')} pages)")
    
    embed = discord.Embed(
        title=f"🧸📚 {ctx.author.display_name}'s {length_display} Books",
        description="\n".join(book_list),
        color=discord.Color.blue()
    )
    
    if len(matches) > items_per_page:
        embed.set_footer(text=f"Showing {len(book_list)} of {len(matches)} books")
    else:
        embed.set_footer(text=f"Total: {len(matches)} books")
    
    await ctx.send(embed=embed)

@bot.command()
async def length_stats(ctx):
    """Get statistics about book lengths in your library"""
    books = get_book_list_for_user(ctx)
    if books is None:
        await ctx.send("🧸📚 You don't have a book list set up yet! 🧸💔")
        return
    
    if not books:
        await ctx.send("🧸📚 Button can't find any books in your to-read list! 🧸💔")
        return
    
    total = len(books)
    short = 0
    medium = 0
    long = 0
    unknown = 0
    
    for book in books:
        if book.get('pages') and book['pages'].isdigit():
            pages = int(book['pages'])
            if pages < 300:
                short += 1
            elif pages < 500:
                medium += 1
            else:
                long += 1
        else:
            unknown += 1
    
    embed = discord.Embed(
        title=f"📏 {ctx.author.display_name}'s Book Length Stats",
        color=discord.Color.green()
    )
    
    embed.add_field(name="📚 Total Books", value=str(total), inline=True)
    
    if total > 0:
        embed.add_field(
            name="📖 Short (< 300 pages)", 
            value=f"{short} books ({short/total*100:.1f}%)", 
            inline=True
        )
        embed.add_field(
            name="📚 Medium (300-499 pages)", 
            value=f"{medium} books ({medium/total*100:.1f}%)", 
            inline=True
        )
        embed.add_field(
            name="📕 Long (500+ pages)", 
            value=f"{long} books ({long/total*100:.1f}%)", 
            inline=True
        )
    
    if unknown > 0:
        embed.add_field(name="❓ Unknown Length", value=f"{unknown} books", inline=True)
    
    # Find shortest and longest books
    valid_books = [(b, int(b['pages'])) for b in books if b.get('pages') and b['pages'].isdigit()]
    if valid_books:
        shortest = min(valid_books, key=lambda x: x[1])
        longest = max(valid_books, key=lambda x: x[1])
        
        embed.add_field(
            name="📖 Shortest Book",
            value=f"{shortest[0]['title']} — {shortest[1]} pages",
            inline=False
        )
        embed.add_field(
            name="📕 Longest Book",
            value=f"{longest[0]['title']} — {longest[1]} pages",
            inline=False
        )
    
    # Average length
    if valid_books:
        avg_pages = sum(p for _, p in valid_books) / len(valid_books)
        embed.add_field(
            name="📊 Average Length",
            value=f"{avg_pages:.0f} pages",
            inline=True
        )
    
    embed.set_footer(text="🧸 Button loves helping you find the perfect book length! 🧸")
    await ctx.send(embed=embed)

@bot.command()
async def compare_lists(ctx, user1: discord.Member = None, user2: discord.Member = None):
    """Compare two users' book lists and find common interests.
    Usage: *compare_lists @User1 @User2
    If no users are mentioned, compares you with a random user."""
    
    if user1 is None or user2 is None:
        # If only one user is mentioned, compare with a random user
        if user1 is not None and user2 is None:
            # Find another user with a book list
            other_users = [uid for uid in USER_BOOK_FILES.keys() if uid != user1.id]
            if other_users:
                random_user_id = random.choice(other_users)
                random_user = await bot.fetch_user(random_user_id)
                user2 = user1
                user1 = random_user
                await ctx.send(f"🧸 Comparing {user1.display_name}'s list with {user2.display_name}'s list!")
            else:
                await ctx.send("🧸 Not enough users with book lists to compare! 💔")
                return
        else:
            await ctx.send("🧸 Please mention two users to compare lists! Example: *compare_lists @UserA @UserB 💔")
            return
    
    # Check if both users have book lists
    if user1.id not in USER_BOOK_FILES:
        await ctx.send(f"🧸 {user1.display_name} doesn't have a book list set up! 💔")
        return
    if user2.id not in USER_BOOK_FILES:
        await ctx.send(f"🧸 {user2.display_name} doesn't have a book list set up! 💔")
        return
    
    # Get both users' books
    books1 = get_user_books(user1.id)
    books2 = get_user_books(user2.id)
    
    if not books1:
        await ctx.send(f"🧸 {user1.display_name}'s book list is empty! 💔")
        return
    if not books2:
        await ctx.send(f"🧸 {user2.display_name}'s book list is empty! 💔")
        return
    
    # Find common books by title (case insensitive)
    titles1 = {b['title'].lower(): b for b in books1}
    titles2 = {b['title'].lower(): b for b in books2}
    
    common_titles = set(titles1.keys()) & set(titles2.keys())
    common_books = [titles1[title] for title in common_titles]
    
    # Find common authors
    authors1 = set(b['author'].lower() for b in books1)
    authors2 = set(b['author'].lower() for b in books2)
    common_authors = authors1 & authors2
    
    # Find common genres
    genres1 = set()
    genres2 = set()
    for book in books1:
        genres1.update([tag.replace('genre: ', '').lower() for tag in book.get('tags', []) if tag.startswith('genre:')])
    for book in books2:
        genres2.update([tag.replace('genre: ', '').lower() for tag in book.get('tags', []) if tag.startswith('genre:')])
    common_genres = genres1 & genres2
    
    # Find common moods
    moods1 = set()
    moods2 = set()
    for book in books1:
        moods1.update([tag.replace('mood: ', '').lower() for tag in book.get('tags', []) if tag.startswith('mood:')])
    for book in books2:
        moods2.update([tag.replace('mood: ', '').lower() for tag in book.get('tags', []) if tag.startswith('mood:')])
    common_moods = moods1 & moods2
    
    # Create comparison embed
    embed = discord.Embed(
        title="📚 Book List Comparison",
        description=f"Comparing **{user1.display_name}** and **{user2.display_name}**'s reading interests!",
        color=discord.Color.gold()
    )
    
    embed.add_field(
        name=f"📖 {user1.display_name}'s Books",
        value=str(len(books1)),
        inline=True
    )
    embed.add_field(
        name=f"📖 {user2.display_name}'s Books",
        value=str(len(books2)),
        inline=True
    )
    embed.add_field(
        name="📚 Common Books",
        value=f"{len(common_books)} books",
        inline=True
    )
    
    if common_authors:
        author_list = list(common_authors)[:5]
        embed.add_field(
            name="✍️ Common Authors",
            value="\n".join([f"• {a.title()}" for a in author_list]) + (f"\n*and {len(common_authors)-5} more*" if len(common_authors) > 5 else ""),
            inline=False
        )
    
    if common_genres:
        genre_list = list(common_genres)[:5]
        embed.add_field(
            name="🎭 Common Genres",
            value="\n".join([f"• {g.title()}" for g in genre_list]) + (f"\n*and {len(common_genres)-5} more*" if len(common_genres) > 5 else ""),
            inline=False
        )
    
    if common_moods:
        mood_list = list(common_moods)[:5]
        embed.add_field(
            name="💭 Common Moods",
            value="\n".join([f"• {m.title()}" for m in mood_list]) + (f"\n*and {len(common_moods)-5} more*" if len(common_moods) > 5 else ""),
            inline=False
        )
    
    if common_books:
        # Show some common books
        common_list = common_books[:5]
        book_list = []
        for book in common_list:
            book_list.append(f"• {book['title']} — {book['author']}")
        embed.add_field(
            name="📚 Common Books (sample)",
            value="\n".join(book_list) + (f"\n*and {len(common_books)-5} more*" if len(common_books) > 5 else ""),
            inline=False
        )
    
    embed.set_footer(text=f"🧸 Button loves bringing readers together!")
    
    await ctx.send(embed=embed)
    
    # Offer recommendations based on common interests
    if common_books or common_genres or common_authors:
        await asyncio.sleep(1)  # Brief pause
        await ctx.send(f"🧸 Since you have common interests, would you like a recommendation? Use `*rec_common @{user1.display_name} @{user2.display_name}`!")

@bot.command()
async def rec_common(ctx, user1: discord.Member = None, user2: discord.Member = None):
    """Get a book recommendation based on two users' common interests.
    Usage: *rec_common @User1 @User2"""
    
    if user1 is None or user2 is None:
        await ctx.send("🧸 Please mention two users! Example: *rec_common @UserA @UserB 💔")
        return
    
    # Check if both users have book lists
    if user1.id not in USER_BOOK_FILES:
        await ctx.send(f"🧸 {user1.display_name} doesn't have a book list set up! 💔")
        return
    if user2.id not in USER_BOOK_FILES:
        await ctx.send(f"🧸 {user2.display_name} doesn't have a book list set up! 💔")
        return
    
    books1 = get_user_books(user1.id)
    books2 = get_user_books(user2.id)
    
    if not books1 or not books2:
        await ctx.send("🧸 One of the users has an empty book list! 💔")
        return
    
    # Find common interests
    titles1 = {b['title'].lower(): b for b in books1}
    titles2 = {b['title'].lower(): b for b in books2}
    common_titles = set(titles1.keys()) & set(titles2.keys())
    common_books = [titles1[title] for title in common_titles]
    
    # Get common authors
    authors1 = set(b['author'].lower() for b in books1)
    authors2 = set(b['author'].lower() for b in books2)
    common_authors = authors1 & authors2
    
    # Get common genres
    genres1 = set()
    genres2 = set()
    for book in books1:
        genres1.update([tag.replace('genre: ', '').lower() for tag in book.get('tags', []) if tag.startswith('genre:')])
    for book in books2:
        genres2.update([tag.replace('genre: ', '').lower() for tag in book.get('tags', []) if tag.startswith('genre:')])
    common_genres = genres1 & genres2
    
    # Create a combined list of recommended books
    recommended = []
    
    # 1. Books that both users have (already common)
    recommended.extend(common_books)
    
    # 2. Books from user1 that match user2's interests
    if common_genres:
        for book in books1:
            book_genres = [tag.replace('genre: ', '').lower() for tag in book.get('tags', []) if tag.startswith('genre:')]
            if any(g in common_genres for g in book_genres) and book not in recommended:
                recommended.append(book)
    
    # 3. Books from user2 that match user1's interests
    if common_genres:
        for book in books2:
            book_genres = [tag.replace('genre: ', '').lower() for tag in book.get('tags', []) if tag.startswith('genre:')]
            if any(g in common_genres for g in book_genres) and book not in recommended:
                recommended.append(book)
    
    # 4. Books by common authors
    if common_authors:
        for book in books1:
            if book['author'].lower() in common_authors and book not in recommended:
                recommended.append(book)
        for book in books2:
            if book['author'].lower() in common_authors and book not in recommended:
                recommended.append(book)
    
    if not recommended:
        await ctx.send(f"🧸 No common interests found between {user1.display_name} and {user2.display_name}! 💔")
        return
    
    # Pick a random book from the recommendations
    recommended_book = random.choice(recommended)
    
    embed = discord.Embed(
        title="🧸📚 Button's Collaborative Recommendation!",
        description=f"Based on the shared interests of **{user1.display_name}** and **{user2.display_name}**...",
        color=discord.Color.gold()
    )
    
    embed.add_field(name="📖 Book", value=recommended_book['title'], inline=False)
    embed.add_field(name="✍️ Author", value=recommended_book['author'], inline=True)
    
    if recommended_book.get('pages') and recommended_book['pages'].isdigit():
        embed.add_field(name="📄 Pages", value=recommended_book['pages'], inline=True)
    
    # Show genres and moods
    genres = [tag.replace('genre: ', '') for tag in recommended_book.get('tags', []) if tag.startswith('genre:')]
    moods = [tag.replace('mood: ', '') for tag in recommended_book.get('tags', []) if tag.startswith('mood:')]
    
    if genres:
        embed.add_field(name="🎭 Genres", value=', '.join(genres), inline=False)
    if moods:
        embed.add_field(name="💭 Moods", value=', '.join(moods), inline=False)
    
    # Add summary
    if recommended_book.get('summary'):
        summary = recommended_book['summary'][:300] + "..." if len(recommended_book['summary']) > 300 else recommended_book['summary']
        embed.add_field(name="📝 Summary", value=summary, inline=False)
    
    # Show whose list it came from
    if recommended_book in common_books:
        embed.set_footer(text=f"📚 This book is on both {user1.display_name} and {user2.display_name}'s lists!")
    elif recommended_book in books1:
        embed.set_footer(text=f"📚 This book is from {user1.display_name}'s list")
    elif recommended_book in books2:
        embed.set_footer(text=f"📚 This book is from {user2.display_name}'s list")
    
    await ctx.send(embed=embed)

@bot.command()
async def random_user(ctx):
    """Get a random user's book list to explore."""
    users_with_lists = [uid for uid in USER_BOOK_FILES.keys()]
    
    if not users_with_lists:
        await ctx.send("🧸 No users have book lists set up yet! 💔")
        return
    
    random_user_id = random.choice(users_with_lists)
    random_user = await bot.fetch_user(random_user_id)
    
    # Get their books
    books = get_user_books(random_user_id)
    
    embed = discord.Embed(
        title=f"🧸 Random User: {random_user.display_name}",
        description=f"Check out {random_user.display_name}'s reading list!",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="📚 Total Books", value=str(len(books)), inline=True)
    
    # Count genres
    genres = set()
    for book in books:
        genres.update([tag.replace('genre: ', '') for tag in book.get('tags', []) if tag.startswith('genre:')])
    embed.add_field(name="🎭 Genres", value=str(len(genres)), inline=True)
    
    # Show a random book from their list
    if books:
        random_book = random.choice(books)
        embed.add_field(
            name="📖 Random Book from Their List",
            value=f"**{random_book['title']}** — *{random_book['author']}*",
            inline=False
        )
    
    embed.set_footer(text="🧸 Use *compare_lists to compare your list with theirs!")
    
    await ctx.send(embed=embed)

@bot.command()
async def common_interests(ctx, user: discord.Member = None):
    """See what you have in common with another user.
    Usage: *common_interests @User"""
    
    if user is None:
        await ctx.send("🧸 Please mention a user! Example: *common_interests @UserA 💔")
        return
    
    if user.id == ctx.author.id:
        await ctx.send("🧸 You can't compare with yourself! Try *compare_lists @UserA @UserB instead. 💔")
        return
    
    # Check if both users have book lists
    if ctx.author.id not in USER_BOOK_FILES:
        await ctx.send(f"🧸 You don't have a book list set up yet! 💔")
        return
    if user.id not in USER_BOOK_FILES:
        await ctx.send(f"🧸 {user.display_name} doesn't have a book list set up! 💔")
        return
    
    await compare_lists(ctx, ctx.author, user)


@bot.command()
async def commands(ctx):
    # Part 1: Cozy commands, Daily commands, Birthdays
    part1 = (
        "🧸 **Button's Commands** 🧸\n\n"
        
        "**💗 Cozy & Social**\n"
        "*hug [@user] - Send a virtual hug to someone or receive one from Button\n"
        "*goodmorning [@user] - Send a good morning message to someone or receive one from Button\n"
        "*goodnight [@user] - Send a goodnight message to someone or receive one from Button\n\n"
        
        "**🌙 Daily & Mood**\n"
        "*mood - Check Button's mood for the day\n"
        "*mystery - Discover Button's mystery of the day\n"
        "*dream - Check what Button is dreaming about\n"
        "*drink - Learn what kind of beverage Button is drinking\n\n"
        
        "**🎂 Birthdays**\n"
        "*birthday [@user] - Check a birthday\n"
        "*add_birthday [@user] [DD/MM] - Add a birthday (admin only)\n"
        "*edit_birthday [@user] [DD/MM] - Edit a birthday (admin only)\n"
        "*remove_birthday [@user] - Remove a birthday (admin only)\n"
        "*list_birthdays - List all birthdays"
    )
    
    # Part 2: Book Management
    part2 = (
        "**📚 Your Personal Book Management**\n"
        "*mybooks - Check if you have a book list\n"
        "*recommend - Get a random book from your list\n"
        "*list_books [page] - List your books alphabetically with interactive pagination\n"
        "*search_book <title> - Search your books by title\n"
        "*book_info <title> - Get full info about a book\n"
        "*summary <title> - Get the full summary of a book\n\n"
        
        "**✏️ Adding & Editing Books**\n"
        "*add_book Title | Author | Pages | Series - Add a book\n"
        "  • Example: *add_book The Hobbit | J.R.R. Tolkien | 310 | Middle Earth\n"
        "  • Only the title is required\n"
        "*remove_book <title> - Remove a book\n"
        "*edit_book Old Title | field | new value - Edit a book\n"
        "  • Example: *edit_book The Hobbit | pages | 310\n"
        "*add_genre Book Title | Genre - Add a genre\n"
        "*remove_genre Book Title | Genre - Remove a genre\n"
        "*add_mood Book Title | Mood - Add a mood\n"
        "*remove_mood Book Title | Mood - Remove a mood"
    )
    
    # Part 3: Stats, Recommendations, Social
    part3 = (
        "**📊 Library Statistics**\n"
        "*library_stats - Get stats for your library\n"
        "*length_stats - Get length statistics\n"
        "*list_genres - List all genres\n"
        "*list_moods - List all moods\n"
        "*list_length <short|medium|long> - List books by length\n\n"
        
        "**🎯 Smart Recommendations**\n"
        "*recommendmood <mood> - Recommend by mood (e.g., dark)\n"
        "*recommendgenre <genre> - Recommend by genre (e.g., fantasy)\n"
        "*recommendlength <short|medium|long> - Recommend by length\n\n"
        
        "**👥 Social Book Features**\n"
        "*compare_lists @UserA @UserB - Compare two users' lists\n"
        "*rec_common @UserA @UserB - Recommend based on common interests\n"
        "*common_interests @User - See what you have in common\n"
        "*random_user - Explore a random user's list\n\n"
        
        "**🔄 Other**\n"
        "*refresh_books - Reload your book data\n"
        "*my_id - Get your Discord User ID\n\n"
        
        "**💡 Tips:**\n"
        "• Use `|` as a separator for commands with multiple fields\n"
        "• Example: *add_book The Hobbit | J.R.R. Tolkien | 310 | Middle Earth\n"
        "• You can only edit your own books\n\n"
        
        "**📖 Help**\n"
        "*commands - Show this list"
    )
    
    # Send all three messages
    await ctx.send(part1)
    await ctx.send(part2)
    await ctx.send(part3)   

keep_alive()
bot.run(os.getenv("TOKEN"))