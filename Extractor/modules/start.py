from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from config import BOT_USERNAME
from Extractor import app

custom_button = [[
                  InlineKeyboardButton("🎯 CʟᴀssPʟᴜs 🎯", callback_data="cpwp")
                ],[
                  InlineKeyboardButton("𝐁 𝐀 𝐂 𝐊", callback_data="modes_")
                ]]

@app.on_message(filters.command("start"))
async def start(bot, message: Message):
    await message.reply_text(
        text=f"Hello {message.from_user.mention},\n\nI am {BOT_USERNAME}. Click the button below to start.",
        reply_markup=InlineKeyboardMarkup(custom_button)
    )