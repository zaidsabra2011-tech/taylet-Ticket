import os
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import discord
from discord.ext import commands
from discord.ui import Select, View, Button

# 1. Dummy HTTP Server for Render
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Ticket Bot is Active!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_http_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

threading.Thread(target=run_http_server, daemon=True).start()

# 2. Discord Bot Setup
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Close Ticket Button
class CloseTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="إغلاق التكت 🔒", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("سيتم إغلاق التكت خلال 5 ثوانٍ...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

# Dropdown Selection
class TicketSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="نقل فردي 🔴", value="individual", description="تقديم طلب نقل شخصي"),
            discord.SelectOption(label="نقل جروب 🔴", value="group", description="تقديم طلب نقل مجموعة/كلان"),
        ]
        super().__init__(placeholder="اختر نوع التكت...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        category_name = "TICKETS"

        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        ticket_type = "فردي" if self.values[0] == "individual" else "جروب"
        channel_name = f"ticket-{user.name}"
        
        ticket_channel = await guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)
        
        await interaction.response.send_message(f"تم إنشاء تكتك بنجاح: {ticket_channel.mention}", ephemeral=True)

        embed = discord.Embed(
            title=f"تكت نقل - {ticket_type}",
            description=f"أهلاً بك {user.mention}، يرجى كتابة تفاصيل طلبك وسيتم الرد عليك قريباً.",
            color=discord.Color.red()
        )
        await ticket_channel.send(embed=embed, view=CloseTicketView())

class TicketPanel(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

# Command to send panel
@bot.command()
@commands.has_permissions(administrator=True)
async def setup_ticket(ctx):
    await ctx.message.delete()
    embed = discord.Embed(
        title="نظام التكتات والطلبات",
        description="يرجى اختيار قسم التكت المناسب من القائمة أدناه لفتح تكت جديد.",
        color=discord.Color.dark_theme()
    )
    await ctx.send(embed=embed, view=TicketPanel())

token = os.environ.get("BOT_TOKEN")
bot.run(token)
