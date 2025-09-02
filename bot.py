import os
import asyncio
from fastapi import FastAPI
import uvicorn
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.enums import ChatMemberStatus

# === CONFIG UIT ENVIRONMENT VARIABLES ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))  # bv. -1001234567890
PRIVATE_GROUP_LINK = os.getenv("PRIVATE_GROUP_LINK", "https://t.me/+Le8og-ss9-pkYjFk")
PUBLIC_GROUP_LINK = os.getenv("PUBLIC_GROUP_LINK", "https://t.me/myometvhack")

if not BOT_TOKEN or not GROUP_ID:
    raise ValueError("❌ BOT_TOKEN en GROUP_ID moeten als environment variables ingesteld zijn!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Opslag in RAM
user_invites = {}  # { user_id: {"count": int, "invite_link": str} }

# === Functie om persoonlijke invite link te maken of ophalen ===
async def get_or_create_invite(user_id: int):
    if user_id in user_invites and "invite_link" in user_invites[user_id]:
        return user_invites[user_id]["invite_link"]

    invite = await bot.create_chat_invite_link(
        chat_id=GROUP_ID,
        creates_join_request=False,
        name=f"Invite_by_{user_id}"
    )
    user_invites[user_id] = {"count": 0, "invite_link": invite.invite_link}
    return invite.invite_link


# === Nieuwe members event ===
@dp.chat_member()
async def new_member(event: types.ChatMemberUpdated):
    if event.new_chat_member.status == ChatMemberStatus.MEMBER:
        inviter = event.invite_link.creator if event.invite_link else None

        # Alleen tellen via persoonlijke invite link
        if inviter and inviter.id in user_invites:
            inviter_id = inviter.id
            user_invites[inviter_id]["count"] += 1
            count = user_invites[inviter_id]["count"]

            if count < 2:
                btn = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=f"Share to unlock Instructions ({count}/2)",
                        url=user_invites[inviter_id]["invite_link"]
                    )]
                ])
                await bot.send_message(
                    inviter_id,
                    f"🔥 Je hebt nu {count}/2 mensen uitgenodigd! Deel de link nog een keer om toegang te krijgen.",
                    reply_markup=btn
                )
            else:
                btn = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Open private group", url=PRIVATE_GROUP_LINK)]
                ])
                await bot.send_message(
                    inviter_id,
                    "🎉 Je hebt 2 invites gehaald en toegang tot de private group gekregen!",
                    reply_markup=btn
                )
        else:
            # Publieke link join → negeren
            await bot.send_message(
                GROUP_ID,
                f"ℹ️ {event.new_chat_member.user.first_name} is via de publieke link binnengekomen (telt niet mee voor invites)."
            )


# === Verwijder publieke link berichten ===
@dp.message()
async def block_public_link(message: types.Message):
    if PUBLIC_GROUP_LINK in message.text:
        try:
            await message.delete()
            await message.answer(
                f"🚫 De publieke invite link mag hier niet gedeeld worden!\n"
                f"Gebruik je persoonlijke link via de bot om invites te verdienen."
            )
        except Exception:
            pass  # Als bot geen permissies heeft


# === /start command ===
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    try:
        # Check privé chat
        if message.chat.type != "private":
            await message.reply("ℹ️ Stuur /start in privé chat met de bot om je persoonlijke invite link te krijgen.")
            return

        invite_link = await get_or_create_invite(message.from_user.id)

        btn = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Share to unlock Instructions (0/2)", url=invite_link)]
        ])

        await message.answer(
            "🚀 Share *your personal invite link* to 2 people to unlock the private group.\n\n"
            "⚠️ Joining via the public link does not count!",
            reply_markup=btn,
            parse_mode="Markdown"
        )
    except Exception as e:
        await message.answer(f"❌ Er is een fout opgetreden: {e}")


# === FastAPI dummy server (Render verwacht webservice) ===
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "Bot running ✅"}


# === Start bot + webserver ===
async def start_bot():
    print("🤖 Bot is gestart en draait op Render Web Service...")
    await dp.start_polling(bot)

def start():
    loop = asyncio.get_event_loop()
    loop.create_task(start_bot())
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))

if __name__ == "__main__":
    start()
