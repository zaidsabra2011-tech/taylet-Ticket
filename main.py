import os
import asyncio
import threading
import discord
from discord.ext import commands
from discord.ui import Select, View, Button
from http.server import HTTPServer, SimpleHTTPRequestHandler

# --- الإعدادات المخصصة ---
TARGET_VOICE_CHANNEL_ID = 1525434137769676912  # آيدي الروم الصوتي للبوت
AUTO_ROLE_ID = 1525607421886726235           # آيدي رتبة الأعضاء الجدد التلقائية
ALLOWED_ROLE_IDS = [1539434561455394907, 1533833117369110610]  # رتب الإدارة المسموح لها استخدام الأوامر

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
intents.members = True

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


# --- نظام الأسباب عبر قائمة منسدلة (Select Menu) ---
class ReasonSelect(Select):
    def __init__(self, action_type, member, duration=None):
        self.action_type = action_type
        self.member = member
        self.duration = duration
        options = [
            discord.SelectOption(label="قذف", description="سبب العقوبة: قذف وسب", emoji="🔴", value="قذف"),
            discord.SelectOption(label="اسلوب سئ", description="سبب العقوبة: التعامل بأسلوب سيء", emoji="🟠", value="اسلوب سئ"),
            discord.SelectOption(label="خاص", description="سبب العقوبة: مخالفة قوانين الخاص", emoji="🟡", value="خاص"),
        ]
        super().__init__(placeholder="اختر سبب العقوبة من القائمة...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        reason = self.values[0]
        try:
            # 1. حذف رسالة القائمة فوراً عند اختيار السبب
            try:
                await interaction.message.delete()
            except:
                pass

            # 2. تنفيذ العقوبة وإرسال رسالة مؤقتة تختفي بعد 5 ثوانٍ
            if self.action_type == "ban":
                await self.member.ban(reason=reason)
                msg = await interaction.channel.send(f"🔨 تم تبنيد العضو {self.member.mention}\n📝 السبب: `{reason}`")
            elif self.action_type == "kick":
                await self.member.kick(reason=reason)
                msg = await interaction.channel.send(f"👢 تم طرد العضو {self.member.mention}\n📝 السبب: `{reason}`")
            elif self.action_type == "timeout":
                duration_time = discord.utils.utcnow() + discord.timedelta(minutes=self.duration)
                await self.member.timeout(duration_time, reason=reason)
                msg = await interaction.channel.send(f"🔇 تم إعطاء تايم أوت للعضو {self.member.mention} لمدة `{self.duration}` دقيقة\n📝 السبب: `{reason}`")
            
            # حذف رسالة النتيجة بعد 5 ثواني لتنظيف الشات تماماً
            await asyncio.sleep(5)
            try:
                await msg.delete()
            except:
                pass

        except Exception as e:
            await interaction.response.send_message(f"❌ حدث خطأ أثناء تنفيذ العقوبة: {e}", ephemeral=True)

class ReasonView(View):
    def __init__(self, action_type, member, duration=None):
        super().__init__(timeout=30)
        self.add_item(ReasonSelect(action_type, member, duration))


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    
    # محاولة دخول الروم مع إعادة المحاولة لضمان الاتصال
    for attempt in range(5):
        await asyncio.sleep(3)
        channel = bot.get_channel(TARGET_VOICE_CHANNEL_ID)
        if not channel:
            for guild in bot.guilds:
                channel = guild.get_channel(TARGET_VOICE_CHANNEL_ID)
                if channel:
                    break
                    
        if channel and isinstance(channel, discord.VoiceChannel):
            try:
                if not channel.guild.voice_client:
                    await channel.connect(self_deaf=True)
                    print(f"Successfully joined voice channel: {channel.name}")
                    break
                else:
                    await channel.guild.voice_client.move_to(channel)
                    print(f"Moved to voice channel: {channel.name}")
                    break
            except Exception as e:
                print(f"Attempt {attempt+1} failed to join voice: {e}")


# --- إعطاء الرتبة التلقائية عند دخول عضو جديد ---
@bot.event
async def on_member_join(member):
    role = member.guild.get_role(AUTO_ROLE_ID)
    if role:
        try:
            await member.add_roles(role)
        except Exception as e:
            print(f"Failed to auto-assign role: {e}")


# --- دالة التحقق من الصلاحيات ---
def has_admin_or_allowed_role(member):
    if member.guild_permissions.administrator:
        return True
    return any(role.id in ALLOWED_ROLE_IDS for role in member.roles)


# --- أوامر التكتات والمسح ---

@bot.command()
async def setup_ticket(ctx):
    if not has_admin_or_allowed_role(ctx.author):
        return await ctx.send(f"❌ {ctx.author.mention}, ليس لديك صلاحية لاستخدام هذا الأمر!", delete_after=5)
    
    await ctx.message.delete()
    embed = discord.Embed(
        title="🎫 نظام التكت والدعم الفني",
        description="أهلاً بك! يرجى اختيار القسم المناسب لطلبك من القائمة أدناه لفتح تكت تواصل مع الإدارة.",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Taylet Ultimate Bot")
    await ctx.send(embed=embed, view=TicketPanel())


@bot.command(name="مسح", aliases=["clear"])
async def clear(ctx, amount: int = 10):
    if not has_admin_or_allowed_role(ctx.author) and not ctx.author.guild_permissions.manage_messages:
        return await ctx.send(f"❌ {ctx.author.mention}, ليس لديك صلاحية لاستخدام هذا الأمر!", delete_after=5)
        
    await ctx.message.delete()
    deleted = await ctx.channel.purge(limit=amount)
    msg = await ctx.send(f"🧹 تم مسح `{len(deleted)}` رسالة بنجاح.")
    await asyncio.sleep(5)
    await msg.delete()


# --- أوامر العقوبات ---

@bot.command(name="ban")
async def ban(ctx, member: discord.Member = None):
    if not has_admin_or_allowed_role(ctx.author):
        await ctx.message.delete()
        return await ctx.send(f"❌ {ctx.author.mention}, ليس لديك صلاحية لاستخدام هذا الأمر!", delete_after=5)
    
    if not member:
        return await ctx.send("❌ يرجى منشن العضو أو وضع آيديه، مثال: `!ban @user`", delete_after=5)

    await ctx.message.delete()
    view = ReasonView("ban", member)
    await ctx.send(f"📌 اختر سبب تبنيد العضو {member.mention}:", view=view)


@bot.command(name="kick")
async def kick(ctx, member: discord.Member = None):
    if not has_admin_or_allowed_role(ctx.author):
        await ctx.message.delete()
        return await ctx.send(f"❌ {ctx.author.mention}, ليس لديك صلاحية لاستخدام هذا الأمر!", delete_after=5)
    
    if not member:
        return await ctx.send("❌ يرجى منشن العضو أو وضع آيديه، مثال: `!kick @user`", delete_after=5)

    await ctx.message.delete()
    view = ReasonView("kick", member)
    await ctx.send(f"📌 اختر سبب طرد العضو {member.mention}:", view=view)


@bot.command(name="timeout", aliases=["ميوت"])
async def timeout(ctx, member: discord.Member = None, minutes: int = 5):
    if not has_admin_or_allowed_role(ctx.author):
        await ctx.message.delete()
        return await ctx.send(f"❌ {ctx.author.mention}, ليس لديك صلاحية لاستخدام هذا الأمر!", delete_after=5)
        
    if not member:
        return await ctx.send("❌ يرجى منشن العضو، مثال: `!timeout @user 10`", delete_after=5)

    await ctx.message.delete()
    view = ReasonView("timeout", member, minutes)
    await ctx.send(f"📌 اختر سبب إعطاء التايم أوت للعضو {member.mention}:", view=view)


token = os.environ.get("BOT_TOKEN")
if token:
    bot.run(token)
