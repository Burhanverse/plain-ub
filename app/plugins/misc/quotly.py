from app import BOT, bot, Message, Convo, LOGGER


@bot.add_cmd(cmd=["q", "rq", "fq"])
async def quote_sticker(bot: BOT, message: Message):
    """Create quote stickers with various modes
    
    Usage:
    - q [reply to message] - Simple quote sticker
    - rq [reply to message] - Quote with replied message context
    - fq [username/user_id] [text] - Fake quote with custom user and text
    """
    
    # Get command and input
    parts = message.text.split()
    cmd = parts[0][1:]  # Remove the '/' prefix
    reply = message.reply_to_message
    text_input = " ".join(parts[1:]) if len(parts) > 1 else ""
    
    if cmd == "q":
        # Simple quote - reply to message required
        if not reply:
            return await message.reply("<b>ERROR:</b> <i>Reply to a message to create quote sticker</i>")
        quote_text = reply.text or reply.caption or "Media message"
        
    elif cmd == "rq":
        # Quote with replied message context
        if not reply:
            return await message.reply("<b>ERROR:</b> <i>Reply to a message to create quote sticker with context</i>")
        quote_text = reply.text or reply.caption or "Media message"
        
    elif cmd == "fq":
        # Fake quote - needs user and text
        if not text_input:
            return await message.reply(
                "<b>Usage:</b> <code>fq [username/user_id] [text]</code>\n"
                "<b>Example:</b> <code>fq @username Hello world!</code>"
            )
        
        parts = text_input.split(maxsplit=1)
        if len(parts) < 2:
            return await message.reply("<b>ERROR:</b> <i>Provide both username and text for fake quote</i>")
            
        username = parts[0]
        quote_text = parts[1]
        
        # Try to get user info for fake quotes (optional)
        try:
            if username.startswith("@"):
                user = await bot.get_chat(username)
            else:
                user = await bot.get_chat(int(username))
        except:
            pass
    
    # Create simple quote sticker using QuotLyBot
    status_msg = await message.reply("<code>Creating quote sticker...</code>")
    
    try:
        async with Convo(
            client=bot,
            chat_id="@QuotLyBot",
            filters=None,
            timeout=30
        ) as convo:
            
            # Send the text to quote
            await convo.send_message(text=quote_text)
            
            # Wait for response
            response = await convo.get_response(timeout=30)
            
            if response and response.sticker:
                await message.reply_sticker(response.sticker.file_id)
                await status_msg.delete()
            else:
                await status_msg.edit("<b>ERROR:</b> <i>Failed to create quote sticker</i>")
                
    except Exception as e:
        error_msg = str(e)
        if "blocked" in error_msg.lower():
            await status_msg.edit("<b>ERROR:</b> <i>Please unblock @QuotLyBot and try again</i>")
        else:
            await status_msg.edit(f"<b>ERROR:</b> <i>{error_msg}</i>")


@bot.add_cmd(cmd="qbot")
async def quotly_bot(bot: BOT, message: Message):
    """Create a quote sticker using @QuotLyBot
    
    Usage:
    - qbot [reply to message] - Quote single message
    - qbot [text] - Quote custom text
    - qbot [number] [reply to message] - Quote multiple messages (up to 10)
    """
    
    # Check if we have input or reply
    reply = message.reply_to_message
    text_input = " ".join(message.text.split()[1:]) if len(message.text.split()) > 1 else ""
    
    if not reply and not text_input:
        return await message.reply(
            "<b>Usage:</b>\n"
            "<code>qbot</code> <i>[reply to message]</i>\n"
            "<code>qbot [text]</code> <i>to quote custom text</i>\n"
            "<code>qbot [number]</code> <i>[reply to message] to quote multiple messages</i>"
        )
    
    # Determine what to quote
    messages_to_forward = []
    custom_text = ""
    
    if reply and text_input and text_input.isdigit():
        # Quote multiple messages starting from replied message
        num_messages = min(int(text_input), 10)  # Limit to 10 messages
        messages_to_forward = [reply.id]
        
        # Get additional messages if requested
        if num_messages > 1:
            try:
                async for msg in bot.get_chat_history(
                    message.chat.id, 
                    limit=num_messages - 1, 
                    offset_id=reply.id
                ):
                    if msg.id != message.id:
                        messages_to_forward.append(msg.id)
            except Exception as e:
                LOGGER.warning(f"Failed to get chat history: {e}")
                
    elif reply and not text_input:
        # Quote single replied message
        messages_to_forward = [reply.id]
        
    elif text_input:
        # Quote custom text
        custom_text = text_input
        
    else:
        return await message.reply("<b>ERROR:</b> <i>Provide text or reply to a message to quote</i>")
    
    # Start the quoting process
    status_msg = await message.reply("<code>Creating quote...</code>")
    
    try:
        # Start conversation with QuotLyBot
        async with Convo(
            client=bot,
            chat_id="@QuotLyBot",
            filters=None,
            timeout=30
        ) as convo:
            
            # Send messages or text to bot
            if messages_to_forward:
                # Forward messages to QuotLyBot
                try:
                    await bot.forward_messages(
                        chat_id="@QuotLyBot",
                        from_chat_id=message.chat.id,
                        message_ids=messages_to_forward
                    )
                except Exception as e:
                    await status_msg.edit(f"<b>ERROR:</b> <i>Failed to forward messages: {e}</i>")
                    return
                    
            elif custom_text:
                # Send custom text to QuotLyBot
                await convo.send_message(text=custom_text)
            
            # Wait for the bot's response
            try:
                response = await convo.get_response(timeout=30)
                
                if response and response.sticker:
                    # Send the quote sticker
                    await message.reply_sticker(response.sticker.file_id)
                    await status_msg.delete()
                else:
                    await status_msg.edit("<b>ERROR:</b> <i>QuotLyBot didn't send a sticker, try again</i>")
                    
            except Exception as e:
                await status_msg.edit(f"<b>ERROR:</b> <i>Failed to get response from QuotLyBot: {e}</i>")
                
    except Exception as e:
        error_msg = str(e)
        if "USER_IS_BLOCKED" in error_msg or "blocked" in error_msg.lower():
            await status_msg.edit(
                "<b>ERROR:</b> <i>QuotLyBot is blocked! Please unblock @QuotLyBot and try again</i>"
            )
        elif "FLOOD_WAIT" in error_msg:
            await status_msg.edit("<b>ERROR:</b> <i>Rate limited by QuotLyBot, try again later</i>")
        else:
            await status_msg.edit(f"<b>ERROR:</b> <i>{error_msg}</i>")
            LOGGER.error(f"QuotLy error: {error_msg}")
