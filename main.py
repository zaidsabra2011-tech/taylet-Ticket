import os
import asyncio
import threading
import discord
from discord.ext import commands
from discord.ui import Select, View, Button
from http.server import HTTPServer, SimpleHTTPRequestHandler

# 1. Simple HTTP Server for Render Keep-Alive
class SimpleHTTPRequestHandlerCustom(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Ultimate Bot is Active!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_http_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandlerCustom)
    server.serve_forever()

threading.Thread(target=run_http_server, daemon=True).start()


# 2. Discord Bot Setup
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)


# 3. Ticket Control View (Close & Claim)
class TicketControlView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="استلام التكت 🛄", style=discord.ButtonStyle.green, custom_id="claim_ticket_btn")
    async def claim_button(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ عذراً، هذا الزر مخصص للإدارة فقط!", ephemeral=True)
            return

        button.disabled = True
        button.label = f"تم الاستلام بواسطة {interaction.user.name}"
        await interaction.response.edit_message(view=self)
        await interaction.channel.send(f"✅ تم استلام التكت بواسطة الإدارة: {interaction.user.mention}")

    @discord.ui.button(label="إغلاق التكت 🔒", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn")
    async def close_button(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ عذراً، لا يمكنك إغلاق التكت، مخصص للإدارة فقط!", ephemeral=True)
            return

        await interaction.response.send_message("⏳ سيتم إغلاق التكت خلال 5 ثوانٍ...", ephemeral=False)
        await asyncio.sleep(5)
        await interaction.channel.delete()


# 4. Custom Ticket Options
class TicketSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="دعم فني", description="للحصول على مساعدة وحل المشاكل الفنية", emoji="🛠️", value="دعم-فني"),
            discord.SelectOption(label="استفسارات عامة", description="لأي أسئلة أو استفسارات عامة", emoji="❓", value="استفسارات-عامة"),
            discord.SelectOption(label="شكاوى واقتراحات", description="تقديم شكوى أو اقتراح للإدارة", emoji="📢", value="شكاوى-واقتراحات"),
        ]
        super().__init__(placeholder="اختر نوع التكت من القائمة...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        selected_type = self.values[0]

        category = discord.utils.get(guild.categories, name="TICKETS")
        if not category:
            category = await guild.create_category("TICKETS")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        channel_name = f"{selected_type}-{user.name}"
        channel = await guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)

        embed = discord.Embed(
            title=f"🎫 تكت جديدة : {selected_type}",
            description=f"مرحباً {user.mention}! يرجى كتابة تفاصيل طلبك وسيقوم فريق الدعم بالرد عليك قريباً. تم فتح التكت بنجاح.",
            color=discord.Color.green()
        )

        await channel.send(embed=embed, view=TicketControlView())
        await interaction.response.send_message(f"✅ تم فتح التكت الخاصة بك هنا: {channel.mention}", ephemeral=True)


class TicketPanel(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    
    # الدخول التلقائي للروم المحدد فور تشغيل البوت
    target_channel_id = 1525434040822403283
    channel = bot.get_channel(target_channel_id)
    
    if channel and isinstance(channel, discord.VoiceChannel):
        if not discord.utils.get(bot.voice_clients, guild=channel.guild):
            try:
                await channel.connect(self_deaf=True)
                print(f"Successfully joined voice channel: {channel.name}")
            except Exception as e:
                print(f"Failed to join voice channel: {e}")
    else:
        print("Voice channel not found or invalid ID.")


# --- أوامر التكتات والمسح ---

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_ticket(ctx):
    await ctx.message.delete()
    embed = discord.Embed(
        title="🎫 نظام التكت والدعم الفني",
        description="أهلاً بك! يرجى اختيار القسم المناسب لطلبك من القائمة أدناه لفتح تكت تواصل مع الإدارة.",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Taylet Ultimate Bot")
    await ctx.send(embed=embed, view=TicketPanel())


@bot.command(name="مسح", aliases=["clear"])
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):
    await ctx.message.delete()
    deleted = await ctx.channel.purge(limit=amount)
    msg = await ctx.send(f"🧹 تم حذف `{len(deleted)}` رسالة بنجاح.")
    await asyncio.sleep(3)
    await msg.delete()


token = os.environ.get("BOT_TOKEN")
if token:
    bot.run(token)
