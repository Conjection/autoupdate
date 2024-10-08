import discord
from discord.ext import commands
import os
import requests
import subprocess
import sys
import logging
import atexit
import asyncio
from dotenv import load_dotenv
from tqdm import tqdm
from colorama import Fore, Style, init
import time

# Load environment variables from .env file
load_dotenv()

# Initialize colorama for colored outpu
init()

# GitHub Repository Details
GITHUB_REPO = "Conjection/autoupdate"
LOCAL_VERSION_FILE = "version.txt"
REMOTE_VERSION_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/version.txt"
REMOTE_SCRIPT_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/code.py"

# Webhook URL from environment variables
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# Bot token from environment variables
TOKEN = os.getenv('DISCORD_TOKEN')

# Channel ID from environment variables
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))

# Role ID and User ID from environment variables
ALLOWED_ROLE_ID = int(os.getenv('ALLOWED_ROLE_ID'))
ALLOWED_USER_ID = int(os.getenv('ALLOWED_USER_ID'))

# Define the logging handler for sending logs to a Discord webhook
class WebhookHandler(logging.Handler):
    def __init__(self, webhook_url):
        super().__init__()
        self.webhook_url = webhook_url

    def emit(self, record):
        log_entry = self.format(record)
        payload = {'content': log_entry}
        try:
            requests.post(self.webhook_url, json=payload)
        except Exception as e:
            print(f"Could not send log to webhook: {e}")

# Configure logging
logger = logging.getLogger('my_bot')
logger.setLevel(logging.INFO)  # Set the root logger level to INFO

# Console handler for general info
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

# File handler for errors
file_handler = logging.FileHandler('errors.log', encoding='utf-8', mode='w')
file_handler.setLevel(logging.ERROR)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Webhook handler for all logs
if WEBHOOK_URL:
    webhook_handler = WebhookHandler(WEBHOOK_URL)
    webhook_handler.setLevel(logging.INFO)  # Set webhook handler to INFO level
    webhook_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(webhook_handler)

# Setup bot with bot token and intents
intents = discord.Intents.default()
intents.message_content = True  # Allows the bot to read message content

bot = commands.Bot(command_prefix=None, intents=intents, help_command=None)  # Disable default help command

def loading_bar(duration=2):
    """Show a loading bar with a given duration."""
    for _ in tqdm(range(100), bar_format="{l_bar}%s{bar}%s{r_bar}" % (Fore.BLUE, Style.RESET_ALL), ncols=75):
        time.sleep(duration / 100)

def has_access(user_roles, user_id):
    """Check if the user has the required role or user ID."""
    if any(role.id == ALLOWED_ROLE_ID for role in user_roles) or user_id == ALLOWED_USER_ID:
        return True
    return False

def show_status(success=True):
    """Show status ASCII art with a status indicator."""
    status_circle = Fore.GREEN + "●" + Style.RESET_ALL if success else Fore.RED + "●" + Style.RESET_ALL
    os.system('cls' if os.name == 'nt' else 'clear')  # Clear screen in CLI

    ascii_art = f'''
{Fore.BLUE} ░▒▓██████▓▒░ ░▒▓██████▓▒░▒▓████████▓▒░▒▓██████▓▒░░▒▓█▓▒░░▒▓█▓▒░░▒▓██████▓▒░░▒▓█▓▒░░▒▓█▓▒░░▒▓██████▓▒░░▒▓███████▓▒░░▒▓███████▓▒░  
░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ ░▒▓█▓▒░  ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ 
░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░ ░▒▓█▓▒░  ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ 
░▒▓█▓▒░      ░▒▓████████▓▒░ ░▒▓█▓▒░  ░▒▓█▓▒░      ░▒▓████████▓▒░▒▓█▓▒▒▓███▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓████████▓▒░▒▓███████▓▒░░▒▓█▓▒░░▒▓█▓▒░ 
░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░ ░▒▓█▓▒░  ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ 
░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ ░▒▓█▓▒░  ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ 
 ░▒▓██████▓▒░░▒▓█▓▒░░▒▓█▓▒░ ░▒▓█▓▒░   ░▒▓██████▓▒░░▒▓█▓▒░░▒▓█▓▒░░▒▓██████▓▒░ ░▒▓██████▓▒░░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓███████▓▒░  
{Style.RESET_ALL}'''

    print(ascii_art)
    print(f"Bot Status: {status_circle}")

def get_local_version():
    """Get the local version from the version.txt file."""
    with open(LOCAL_VERSION_FILE, 'r') as f:
        return f.read().strip()

def get_remote_version():
    """Get the remote version from the version.txt file hosted on GitHub."""
    response = requests.get(REMOTE_VERSION_URL)
    response.raise_for_status()
    return response.text.strip()

def download_latest_script():
    """Download the latest version of the script from GitHub."""
    response = requests.get(REMOTE_SCRIPT_URL)
    response.raise_for_status()
    with open("your_script.py", "wb") as f:
        f.write(response.content)

def update_and_restart():
    """Download the latest script and restart."""
    print("Downloading the latest version...")
    download_latest_script()
    print("Update complete. Restarting the script...")
    subprocess.Popen([sys.executable, "your_script.py"])
    sys.exit()

def check_for_updates():
    """Check for updates and update the script if necessary."""
    try:
        local_version = get_local_version()
        remote_version = get_remote_version()

        if local_version != remote_version:
            print(f"New version available: {remote_version} (current version: {local_version})")
            update_and_restart()
        else:
            print("You are running the latest version.")
    except Exception as e:
        logger.error(f"Error checking for updates: {e}")

async def start_bot():
    """Asynchronous function to start the bot and handle CLI display."""
    try:
        logger.info("Starting bot...")
        print(Fore.LIGHTBLUE_EX + "Starting bot..." + Style.RESET_ALL)
        loading_bar()
        show_status(success=True)
        await bot.start(TOKEN)
    except Exception as e:
        show_status(success=False)
        logger.error(f"Error: {e}")
        print(Fore.RED + f"Error: {e}" + Style.RESET_ALL)
        raise

def setup_bot():
    """Setup bot commands and events."""

    @bot.event
    async def on_ready():
        logger.info(f'Bot connected as {bot.user}')
        print(f'Bot connected as {bot.user}')
        activity = discord.Game(name="Baked by Kangal & eaten by Tyrker")
        await bot.change_presence(activity=activity)
        await bot.tree.sync()  # Sync commands with Discord
        logger.info('Bot is now online and ready.')

    def access_check():
        """Decorator to ensure only authorized users can use commands."""
        def predicate(ctx):
            return has_access(ctx.author.roles, ctx.author.id)
        return commands.check(predicate)

    # Function to create and send embed
    async def send_embed(username, user_id, cheat_used, proof, image_link=None):
        channel = bot.get_channel(CHANNEL_ID)
        embed = discord.Embed(title="Cheater Exposed!", color=0x426bb6)  # Color set to #426bb6
        embed.add_field(name="Discord Username", value=username, inline=True)
        embed.add_field(name="Discord ID", value=user_id, inline=True)
        embed.add_field(name="Used Cheat", value=cheat_used, inline=False)
        embed.add_field(name="Proof", value=proof, inline=False)
        if image_link:
            embed.set_image(url=image_link)
        embed.set_footer(text="CatchGuard",
                         icon_url="https://cdn.discordapp.com/attachments/912690524614443008/1276697982804430848/tyktyrkerlogo.png?ex=66cb21e7&is=66c9d067&hm=e9c17c0bf484237490bef663c4e5948fbadb24dc006a1c6d287c39a7a088889e&")
        await channel.send(embed=embed)

    # Slash command to expose cheaters
    @bot.tree.command(name="expose")
    async def expose_slash(interaction: discord.Interaction, username: str, user_id: str, cheat_used: str, proof: str,
                           image_link: str = None):
        logger.info(f"Slash command /expose triggered by {interaction.user}")
        try:
            # Defer the response to acknowledge the interaction
            logger.debug("Deferring interaction response")
            await interaction.response.defer()
            # Send the embed
            logger.debug("Sending embed with cheater information")
            await send_embed(username, user_id, cheat_used, proof, image_link)
            # Send a follow-up message after the embed
            logger.debug("Sending follow-up message")
            await interaction.followup.send("Cheater exposed successfully!")
        except Exception as e:
            logger.error(f"Error handling /expose command: {e}")
            # Send an error message if something goes wrong
            if interaction.response.is_done():
                await interaction.followup.send("An error occurred while processing your request.")
            else:
                await interaction.response.send_message("An error occurred while processing your request.")

    # Command to show credits
    @bot.tree.command(name="credits")
    @access_check()
    async def credits_slash(interaction: discord.Interaction):
        logger.info(f"Slash command /credits triggered by {interaction.user}")
        await interaction.response.send_message("This bot was made by Tyrker and Kangal.")

    # Command to check if the bot is online
    @bot.tree.command(name="ping")
    async def ping_slash(interaction: discord.Interaction):
        logger.info(f"Slash command /ping triggered by {interaction.user}")
        await interaction.response.send_message('The bot is online!')

    # Command to stop the bot
    @bot.tree.command(name="stop")
    @access_check()
    async def stop_slash(interaction: discord.Interaction):
        logger.info(f"Slash command /stop triggered by {interaction.user}")
        await interaction.response.send_message('Bot is shutting down.')
        await bot.close()

setup_bot()

# Handle shutdown
def on_exit():
    logger.info("Bot is shutting down...")
    show_status(success=False)

atexit.register(on_exit)

# Check for updates before starting the bot
check_for_updates()

# Run the bot asynchronously
try:
    asyncio.run(start_bot())
except KeyboardInterrupt:
    logger.info("Bot shut down manually.")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
