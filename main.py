import os
import asyncio
import threading
from datetime import datetime, timedelta
import discord
from discord.ext import commands
from discord.ui import Select, View, Button, Modal, TextInput
from http.server import HTTPServer, SimpleHTTPRequestHandler

# --- الإعدادات المخصصة ---
AUTO_ROLE_ID = 1525607421886726235           
ALLOWED_ROLE_IDS = [1539434561455394907, 1533833117369110610]  
LOG_CHANNEL_ID = 1542839653638606918          

COLOR_ROLE_IDS = [
    1542844911932547092, # لون 1
    1542844920140664845, # لون 2
    1542844920988180480, # لون 3
    1542844921675776080, # لون 4
    1542844922389073951  # لون 5
]

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
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

async def send_log(guild, text):
    try:
        channel = guild.get_channel(LOG_CHANNEL_ID)
        if channel:
            await channel.send(text)
    except Exception as e:
        print(f"Failed to send log: {e}")


# 3. Ticket Control View
class TicketControlView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="استلام التكت 🛄", style=discord.ButtonStyle.green, custom_id="claim_ticket_btn")
    async def claim_button(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.administrator and not any(r.id in ALLOWED_ROLE_IDS for r in interaction.user.roles):
            await interaction.response.send_message("❌ عذراً، هذا الزر مخصص للإدارة فقط!", ephemeral=True)
            return

        button.disabled = True
        button.label = f"تم الاستلام بواسطة {interaction.user.name}"
        await interaction.response.edit_message(view=self)
        await interaction.channel.send(f"✅ تم استلام التكت بواسطة الإدارة: {interaction.user.mention}")
        await send_log(interaction.guild, f"📥 **استلام تكت:** قام المشرف {interaction.user.mention} باستلام التكت في الروم {interaction.channel.mention}")

    @discord.ui.button(label="إغلاق التكت 🔒", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn")
    async def close_button(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.administrator and not any(r.id in ALLOWED_ROLE_IDS for r in interaction.user.roles):
            await interaction.response.send_message("❌ عذراً، لا يمكنك إغلاق التكت، مخصص للإدارة فقط!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        await send_log(interaction.guild, f"🔒 **إغلاق تكت:** قام المشرف {interaction.user.mention} بإغلاق التكت `{interaction.channel.name}`")
        await asyncio.sleep(1)
        await interaction.channel.delete()


# 4. Ticket Select Menu
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
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        await channel.send(embed=embed, view=TicketControlView())
        await interaction.response.send_message(f"✅ تم فتح التكت الخاصة بك هنا: {channel.mention}", ephemeral=True)
        await send_log(guild, f"🎫 **فتح تكت:** العضو {user.mention} فتح تكت جديدة من نوع (`{selected_type}`) في الروم {channel.mention}")


class TicketPanel(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


# --- نظام اختيار الألوان ---
class ColorSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="لون 1", description="اختيار لون 1", emoji="⬛", value=str(COLOR_ROLE_IDS[0])),
            discord.SelectOption(label="لون 2", description="اختيار لون 2", emoji="⬜", value=str(COLOR_ROLE_IDS[1])),
            discord.SelectOption(label="لون 3", description="اختيار لون 3", emoji="🟥", value=str(COLOR_ROLE_IDS[2])),
            discord.SelectOption(label="لون 4", description="اختيار لون 4", emoji="🟦", value=str(COLOR_ROLE_IDS[3])),
            discord.SelectOption(label="لون 5", description="اختيار لون 5", emoji="🔘", value=str(COLOR_ROLE_IDS[4])),
        ]
        super().__init__(placeholder="اختر لونك المفضل من القائمة...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        selected_role_id = int(self.values[0])
        
        selected_role = guild.get_role(selected_role_id)
        if not selected_role:
            return await interaction.response.send_message("❌ الرتبة غير موجودة، يرجى مراجعة الآيديات.", ephemeral=True)

        user_color_roles = [guild.get_role(rid) for rid in COLOR_ROLE_IDS if guild.get_role(rid) in member.roles]
        
        if selected_role in member.roles:
            await member.remove_roles(selected_role)
            await interaction.response.send_message(f"✅ تم إزالة اللون {selected_role.name} منك بنجاح.", ephemeral=True)
        else:
            if user_color_roles:
                await member.remove_roles(*user_color_roles)
            await member.add_roles(selected_role)
            await interaction.response.send_message(f"✅ تم إعطاؤك اللون {selected_role.name} بنجاح.", ephemeral=True)


class ColorPanel(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ColorSelect())


# --- نافذة كتابة السبب (Modal) للعقوبات ---
class ReasonModal(Modal):
    def __init__(self, action_type, member_or_id, duration=None):
        super().__init__(title="حدد سبب العقوبة / الإجراء")
        self.action_type = action_type
        self.member_or_id = member_or_id
        self.duration = duration

        self.reason_input = TextInput(
            label="السبب",
            placeholder="اكتب السبب هنا...",
            style=discord.TextStyle.short,
            required=True,
            max_length=100
        )
        self.add_item(self.reason_input)

    async def on_submit(self, interaction: discord.Interaction):
        reason = self.reason_input.value
        guild = interaction.guild
        admin = interaction.user

        try:
            if self.action_type == "ban":
                await self.member_or_id.ban(reason=reason)
                msg = await interaction.channel.send(f"تم تبنيد العضو {self.member_or_id.mention}\nالسبب: {reason}")
                await send_log(guild, f"🔨 **باند:** قام المشرف {admin.mention} بحظر العضو {self.member_or_id.mention} | السبب: `{reason}`")
                
            elif self.action_type == "unban":
                user = await bot.fetch_user(self.member_or_id)
                await guild.unban(user, reason=reason)
                msg = await interaction.channel.send(f"تم إزالة الحظر عن العضو {user.name}\nالسبب: {reason}")
                await send_log(guild, f"🔓 **فك باند:** قام المشرف {admin.mention} بإلغاء حظر العضو `{user.name}` (`{user.id}`) | السبب: `{reason}`")

            elif self.action_type == "kick":
                await self.member_or_id.kick(reason=reason)
                msg = await interaction.channel.send(f"تم طرد العضو {self.member_or_id.mention}\nالسبب: {reason}")
                await send_log(guild, f"👢 **طرد:** قام المشرف {admin.mention} بطرد العضو {self.member_or_id.mention} | السبب: `{reason}`")
                
            elif self.action_type == "timeout":
                duration_time = discord.utils.utcnow() + timedelta(minutes=self.duration)
                await self.member_or_id.timeout(duration_time, reason=reason)
                msg = await interaction.channel.send(f"تم إعطاء تايم أوت للعضو {self.member_or_id.mention} لمدة {self.duration} دقيقة\nالسبب: {reason}")
                await send_log(guild, f"🔇 **تايم أوت:** قام المشرف {admin.mention} بإعطاء كتم للعضو {self.member_or_id.mention} لمدة `{self.duration}` دقيقة | السبب: `{reason}`")
            
            await asyncio.sleep(5)
            try:
                await msg.delete()
            except:
                pass

        except Exception as e:
            await interaction.response.send_message(f"❌ حدث خطأ أثناء تنفيذ العملية: {e}", ephemeral=True)


class OpenModalButton(View):
    def __init__(self, action_type, member_or_id, duration=None):
        super().__init__(timeout=30)
        self.action_type = action_type
        self.member_or_id = member_or_id
        self.duration = duration

    @discord.ui.button(label="اضغط هنا لكتابة السبب وتأكيد العملية", style=discord.ButtonStyle.blurple)
    async def open_modal(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ReasonModal(self.action_type, self.member_or_id, self.duration))


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


@bot.event
async def on_member_join(member):
    role = member.guild.get_role(AUTO_ROLE_ID)
    if role:
        try:
            await member.add_roles(role)
            await send_log(member.guild, f"👤 **عضو جديد:** انضم العضو {member.mention} وتم إعطاؤه الرتبة التلقائية بنجاح.")
        except Exception as e:
            print(f"Failed to auto-assign role: {e}")


def has_admin_or_allowed_role(member):
    if member.guild_permissions.administrator:
        return True
    return any(role.id in ALLOWED_ROLE_IDS for role in member.roles)


# --- أوامر الإدارة الأساسية ---
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
    if ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)
    embed.set_footer(text="Taylet Ultimate Bot")
    await ctx.send(embed=embed, view=TicketPanel())
    await send_log(ctx.guild, f"⚙️ **إعداد التكتات:** قام المشرف {ctx.author.mention} بإرسال لوحة التكتات.")


@bot.command()
async def setup_colors(ctx):
    if not has_admin_or_allowed_role(ctx.author):
        return await ctx.send(f"❌ {ctx.author.mention}, ليس لديك صلاحية لاستخدام هذا الأمر!", delete_after=5)
    
    await ctx.message.delete()
    embed = discord.Embed(
        title="🎨 نظام اختيار الألوان",
        description="اختر لونك المفضل من القائمة المنسدلة أدناه لتغيير لون رتبتك فوراً!",
        color=discord.Color.purple()
    )
    if ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)
    embed.set_footer(text="Taylet Ultimate Bot")
    await ctx.send(embed=embed, view=ColorPanel())
    await send_log(ctx.guild, f"⚙️ **إعداد الألوان:** قام المشرف {ctx.author.mention} بإرسال لوحة اختيار الألوان.")


@bot.command(name="مسح", aliases=["clear"])
async def clear(ctx, amount: int = 10):
    if not has_admin_or_allowed_role(ctx.author) and not ctx.author.guild_permissions.manage_messages:
        return await ctx.send(f"❌ {ctx.author.mention}, ليس لديك صلاحية لاستخدام هذا الأمر!", delete_after=5)
        
    await ctx.message.delete()
    deleted = await ctx.channel.purge(limit=amount)
    msg = await ctx.send(f"تم مسح {len(deleted)} رسالة بنجاح.")
    await send_log(ctx.guild, f"🧹 **مسح رسائل:** قام المشرف {ctx.author.mention} بحذف `{len(deleted)}` رسالة في الروم {ctx.channel.mention}")
    await asyncio.sleep(5)
    await msg.delete()


@bot.command(name="ban")
async def ban(ctx, member: discord.Member = None):
    if not has_admin_or_allowed_role(ctx.author):
        await ctx.message.delete()
        return await ctx.send(f"❌ {ctx.author.mention}, ليس لديك صلاحية لاستخدام هذا الأمر!", delete_after=5)
    if not member:
        return await ctx.send("❌ يرجى منشن العضو، مثال: `!ban @user`", delete_after=5)
    
    await ctx.message.delete()
    view = OpenModalButton("ban", member)
    msg = await ctx.send(f"انقر على الزر أدناه لتحديد سبب حظر {member.mention}:", view=view)
    await asyncio.sleep(30)
    try:
        await msg.delete()
    except:
        pass


@bot.command(name="unban", aliases=["انبان"])
async def unban(ctx, user_id: int = None):
    if not has_admin_or_allowed_role(ctx.author):
        await ctx.message.delete()
        return await ctx.send(f"❌ {ctx.author.mention}, ليس لديك صلاحية لاستخدام هذا الأمر!", delete_after=5)
    if not user_id:
        return await ctx.send("❌ يرجى كتابة آيدي العضو المراد فك الحظر عنه، مثال: `!unban 123456789123456789`", delete_after=5)
    
    await ctx.message.delete()
    view = OpenModalButton("unban", user_id)
    msg = await ctx.send(f"انقر على الزر أدناه لتحديد سبب فك الحظر عن الآيدي `{user_id}`:", view=view)
    await asyncio.sleep(30)
    try:
        await msg.delete()
    except:
        pass


@bot.command(name="kick")
async def kick(ctx, member: discord.Member = None):
    if not has_admin_or_allowed_role(ctx.author):
        await ctx.message.delete()
        return await ctx.send(f"❌ {ctx.author.mention}, ليس لديك صلاحية لاستخدام هذا الأمر!", delete_after=5)
    if not member:
        return await ctx.send("❌ يرجى منشن العضو، مثال: `!kick @user`", delete_after=5)
    
    await ctx.message.delete()
    view = OpenModalButton("kick", member)
    msg = await ctx.send(f"انقر على الزر أدناه لتحديد سبب طرد {member.mention}:", view=view)
    await asyncio.sleep(30)
    try:
        await msg.delete()
    except:
        pass


@bot.command(name="timeout", aliases=["ميوت"])
async def timeout(ctx, member: discord.Member = None, minutes: int = 5):
    if not has_admin_or_allowed_role(ctx.author):
        await ctx.message.delete()
        return await ctx.send(f"❌ {ctx.author.mention}, ليس لديك صلاحية لاستخدام هذا الأمر!", delete_after=5)
    if not member:
        return await ctx.send("❌ يرجى منشن العضو، مثال: `!timeout @user 10`", delete_after=5)
    
    await ctx.message.delete()
    view = OpenModalButton("timeout", member, minutes)
    msg = await ctx.send(f"انقر على الزر أدناه لتحديد سبب تايم أوت لـ {member.mention}:", view=view)
    await asyncio.sleep(30)
    try:
        await msg.delete()
    except:
        pass


@bot.command(name="untimeout", aliases=["انميوت"])
async def untimeout(ctx, member: discord.Member = None):
    if not has_admin_or_allowed_role(ctx.author):
        await ctx.message.delete()
        return await ctx.send(f"❌ {ctx.author.mention}, ليس لديك صلاحية لاستخدام هذا الأمر!", delete_after=5)
    if not member:
        return await ctx.send("❌ يرجى منشن العضو، مثال: `!untimeout @user`", delete_after=5)
    
    await ctx.message.delete()
    try:
        await member.timeout(None, reason=f"تم إزالة التايم أوت بواسطة {ctx.author.name}")
        msg = await ctx.send(f"تم إزالة التايم أوت عن العضو {member.mention}")
        await send_log(ctx.guild, f"🔊 **إزالة تايم أوت:** قام المشرف {ctx.author.mention} بإزالة التايم أوت عن العضو {member.mention}")
        
        await asyncio.sleep(5)
        try:
            await msg.delete()
        except:
            pass
    except Exception as e:
        await ctx.send(f"❌ حدث خطأ: {e}", delete_after=5)


token = os.environ.get("BOT_TOKEN")
if token:
    bot.run(token)
