import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load token from .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Setup bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Define bot prefix
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    
    # Sync slash commands with Discord
    try:
        synced = await bot.tree.sync()
        print(f'✅ Successfully synced {len(synced)} slash command(s).')
    except Exception as e:
        print(f'❌ Failed to sync slash commands: {e}')
        
    print('------')

# Load cogs automatically
async def load_extensions():
    for filename in os.listdir('./bot/cogs'):
        if filename.endswith('.py'):
            cog_name = f'bot.cogs.{filename[:-3]}'
            try:
                await bot.load_extension(cog_name)
                print(f'Loaded extension: {cog_name}')
            except Exception as e:
                print(f'Failed to load extension {cog_name}: {e}')

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

# Run the bot
if __name__ == '__main__':
    asyncio.run(main())