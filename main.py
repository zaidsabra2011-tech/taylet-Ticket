import os
import asyncio
import threading
import discord
from discord.ext import commands
from discord.ui import Select, View, Button
from http.server import HTTPServer, SimpleHTTPRequestHandler
import yt_dlp

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

# يوتيوب إعدادات البحث والتشغيل
ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'хайрез': False,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# 3. Ticket Control View (Close & Claim)
class TicketControlView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="استلام التكت 🙋‍♂️", style=discord.ButtonStyle.green, custom_id="claim_ticket_btn")
    async def claim_button(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("عذراً، هذا الزر مخصص للإدارة فقط!", ephemeral=True)
            return
        
        button.disabled = True
        button.label = f"تم الاستلام بواسطة {interaction.user.name}"
        await interaction.response.edit_message(view=self)
        await interaction.channel.send(f"✅ تم استلام التكت بواسطة الإداري: {interaction.user.mention}")

    @discord.ui.button(label="إغلاق التكت 🔒", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn")
    async def close_button(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ عذراً، لا يمكنك إغلاق التكت، مخصص للإدارة فقط!", ephemeral=True)
            return

        await interaction.response.send_message("سيتم إغلاق التكت خلال 5 ثوانٍ...", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete()

# 4. Custom Ticket Options
class TicketSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="دعم فني", description="للحصول على مساعدة وحل المشاكل الفنية", emoji="🛠️", value="دعم-فني"),
            discord.SelectOption(label="استفسارات عامة", description="لأي أسئلة أو استفسارات عامة", emoji="❓", value="استفسارات-عامة"),
            discord.SelectOption(label="شكاوى واقتراحات", description="تقديم شكوى أو اقتراح للإدارة", emoji="📝", value="شكاوى-واقتراحات"),
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
            title=f"🎫 تكت جديدة: {selected_type}",
            description=f"مرحباً {user.mention}!\nتم فتح التكت بنجاح.\nيرجى كتابة تفاصيل طلبك وسيقوم فريق الدعم بالرد عليك قريباً.",
            color=discord.Color.green()
        )

        await channel.send(embed=embed, view=TicketControlView())
        await interaction.response.send_message(f"تم فتح التكت الخاصة بك هنا: {channel.mention}", ephemeral=True)

class TicketPanel(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# --- الأوامر المساعدة (تكتات، مسح، صوت) ---

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_ticket(ctx):
    await ctx.message.delete()
    embed = discord.Embed(
        title="نظام التكت والدعم الفني 🎫",
        description="أهلاً بك! يرجى اختيار القسم المناسب لطلبك من القائمة أدناه لفتح تكت تواصل مع الإدارة.",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Taylet Ultimate Bot")
    await ctx.send(embed=embed, view=TicketPanel())

# أمر مسح الرسائل
@bot.command(name="مسح", aliases=["clear"])
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):
    await ctx.message.delete()
    deleted = await ctx.channel.purge(limit=amount)
    msg = await ctx.send(f"🧹 تم حذف `{len(deleted)}` رسالة بنجاح.")
    await asyncio.sleep(3)
    await msg.delete()

# أوامر الصوت والأغاني
@bot.command(name="دخل", aliases=["join"])
async def join(ctx):
    if not ctx.author.voice:
        return await ctx.send("❌ يجب أن تكون متصلاً بروم صوتي أولاً!")
    destination = ctx.author.voice.channel
    if ctx.voice_client:
        await ctx.voice_client.move_to(destination)
    else:
        await destination.connect()
    await ctx.send(f"✅ دخلت الروم الصوتي: **{destination.name}**")

@bot.command(name="شغل", aliases=["play"])
async def play(ctx, *, query):
    if not ctx.voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            return await ctx.send("❌ يجب أن يكون البوت أو أنت في روم صوتي!")
    
    async with ctx.typing():
        try:
            player = await YTDLSource.from_url(query, loop=bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
        except Exception as e:
            return await ctx.send(f"❌ حدث خطأ أثناء تشغيل الأغنية: {e}")

    await ctx.send(f"🎶 جاري تشغيل الآن: **{player.title}**")

@bot.command(name="اطلع", aliases=["leave"])
@commands.has_permissions(administrator=True)
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 تم الخروج من الروم الصوتي.")
    else:
        await ctx.send("❌ البوت ليس في أي روم صوتي أساساً!")

token = os.environ.get("BOT_TOKEN")
if token:
    bot.run(token)
