import os
import asyncio
from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode , ChatMemberStatus
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, UserNotParticipant , UserNotParticipant, ChatAdminRequired , RPCError

from bot import Bot
from config import ADMINS, FORCE_MSG, START_MSG, CUSTOM_CAPTION, DISABLE_CHANNEL_BUTTON, PROTECT_CONTENT, FORCE_SUB_CHANNEL, REQ_JOIN
from helper_func import encode, decode, get_messages, subscribed
from database.database import add_user, del_user, full_userbase, present_user


FORCE_MSG = "Please request to join our private channel using the link below:\n\n{link}"
START_MSG = "Welcome, {first} {last} {username}!"

@Bot.on_message(filters.command('start') & filters.private)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    
    try:
        # Step 1: Generate and provide join request link
        join_link = await client.create_chat_invite_link(chat_id=FORCE_SUB_CHANNEL, creates_join_request=True)
        
        # Step 2: Check if the user's join request is pending
        pending_requests = client.get_chat_join_requests(chat_id=FORCE_SUB_CHANNEL)
        async for request in pending_requests:
            if request.user.id == user_id:
                await message.reply("Your join request is pending approval.")
                return

        # Step 3: Check if the user is already a member
        member_status = await client.get_chat_member(chat_id=FORCE_SUB_CHANNEL, user_id=user_id)
        if member_status.status in ["member", "administrator", "creator"]:
            await message.reply("Welcome back! You are already a member.")
            # Here you can run the logic you intended if the user is a member.
            # Your custom logic code here...
            return

        # If the user is neither in pending requests nor a member, send join link
        buttons = [
            [InlineKeyboardButton("Join Channel", url=join_link.invite_link)],
            [InlineKeyboardButton("Try Again", callback_data="check_membership")]
        ]
        await message.reply(
            text="You need to join the channel first.",
            reply_markup=InlineKeyboardMarkup(buttons),
            quote=True
        )

    except RPCError as e:
        await message.reply(f"An error occurred: {e}")

@Bot.on_callback_query(filters.regex("check_membership"))
async def check_membership(client: Client, callback_query):
    user_id = callback_query.from_user.id

    try:
        # Check again if the user has joined the channel
        member_status = await client.get_chat_member(chat_id=FORCE_SUB_CHANNEL, user_id=user_id)
        if member_status.status in ["member", "administrator", "creator"]:
            await callback_query.message.edit_text("Thanks for joining! You are now a member.")
            # Here you can run the logic you intended if the user is a member.
            # Your custom logic code here...
        else:
            await callback_query.answer("You haven't joined yet. Please join the channel first.", show_alert=True)

    except RPCError as e:
        await callback_query.message.edit_text(f"An error occurred: {e}")

@Bot.on_message(filters.command('users') & filters.private & filters.user(ADMINS))
async def get_users(client: Bot, message: Message):
    msg = await client.send_message(chat_id=message.chat.id, text=WAIT_MSG)
    users = await full_userbase()
    await msg.edit(f"{len(users)} users are using this bot")

@Bot.on_message(filters.private & filters.command('broadcast') & filters.user(ADMINS))
async def send_text(client: Bot, message: Message):
    if message.reply_to_message:
        query = await full_userbase()
        broadcast_msg = message.reply_to_message
        total = 0
        successful = 0
        blocked = 0
        deleted = 0
        unsuccessful = 0
        
        pls_wait = await message.reply("<i>Broadcasting Message.. This will Take Some Time</i>")
        for chat_id in query:
            try:
                await broadcast_msg.copy(chat_id)
                successful += 1
            except FloodWait as e:
                await asyncio.sleep(e.x)
                await broadcast_msg.copy(chat_id)
                successful += 1
            except UserIsBlocked:
                await del_user(chat_id)
                blocked += 1
            except InputUserDeactivated:
                await del_user(chat_id)
                deleted += 1
            except Exception as e:
                unsuccessful += 1
                print(f"Error broadcasting message to {chat_id}: {e}")
            total += 1
        
        status = f"""<b><u>Broadcast Completed</u>

Total Users: <code>{total}</code>
Successful: <code>{successful}</code>
Blocked Users: <code>{blocked}</code>
Deleted Accounts: <code>{deleted}</code>
Unsuccessful: <code>{unsuccessful}</code></b>"""
        
        return await pls_wait.edit(status)

    else:
        msg = await message.reply(REPLY_ERROR)
        await asyncio.sleep(8)
        await msg.delete()
