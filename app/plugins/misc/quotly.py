import io
import textwrap
import requests
from PIL import Image, ImageDraw, ImageFont
from app import BOT, bot, Message, Convo, LOGGER


def get_readable_text(text, width=25):
    """Wrap text to fit within specified width"""
    return "\n".join(textwrap.wrap(text, width))


async def download_profile_photo(client, user_id):
    """Download user's profile photo"""
    try:
        # Get user profile photos
        photos = await client.get_chat_photos(user_id, limit=1)
        if photos:
            # Download the first photo
            photo_path = await client.download_media(photos[0], file_name="temp_pfp.jpg")
            return photo_path
        else:
            # Use default image if no profile photo
            return await download_default_image()
    except Exception as e:
        LOGGER.error(f"Failed to download profile photo: {e}")
        # Use default image
        return await download_default_image()


async def download_default_image():
    """Download default profile image"""
    try:
        default_url = "https://graph.org/file/1fd74fa4a4dbf1655f3ec.jpg"
        response = requests.get(default_url)
        response.raise_for_status()
        with open("temp_pfp.jpg", "wb") as f:
            f.write(response.content)
        return "temp_pfp.jpg"
    except Exception as e:
        LOGGER.error(f"Failed to download default image: {e}")
        return None


@bot.add_cmd(cmd="qpic")
async def quote_pic(bot: BOT, message: Message):
    """Create a quote picture with profile photo"""
    
    reply = message.reply_to_message
    text_input = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""
    
    # Parse flags
    flags = []
    if text_input:
        if "-b" in text_input:
            flags.append("black")
            text_input = text_input.replace("-b", "").strip()
        if "-s" in text_input:
            flags.append("sticker")
            text_input = text_input.replace("-s", "").strip()
    
    # Get text to quote
    if reply and reply.text and not text_input:
        quote_text = reply.text
        user_id = reply.from_user.id if reply.from_user else message.from_user.id
    elif text_input:
        quote_text = text_input
        user_id = message.from_user.id
    else:
        return await message.reply(
            "<b>Usage:</b>\n"
            "<code>qpic</code> <i>[reply to text message]</i>\n"
            "<code>qpic [text]</code> <i>to create quote with custom text</i>\n"
            "<code>qpic -b [text]</code> <i>for black and white output</i>\n"
            "<code>qpic -s [text]</code> <i>to output as sticker</i>"
        )
    
    status_msg = await message.reply("<code>Creating quote picture...</code>")
    
    try:
        # Download profile photo
        pfp_path = await download_profile_photo(bot, user_id)
        if not pfp_path:
            return await status_msg.edit("<b>ERROR:</b> <i>Failed to get profile photo</i>")
        
        # Prepare text
        wrapped_text = get_readable_text(quote_text)
        formatted_text = f'"{wrapped_text}"'
        
        # Create the image
        img = Image.open(pfp_path)
        
        # Convert to black and white if requested
        if "black" in flags:
            img = img.convert("L")
        
        # Resize and prepare
        img = img.convert("RGBA").resize((1024, 1024))
        w, h = img.size
        
        # Create overlay
        nw, nh = 20 * (w // 100), 20 * (h // 100)
        overlay = Image.new("RGBA", (w - nw, h - nh), (0, 0, 0, 150))
        img.paste(overlay, (nw // 2, nh // 2), overlay)
        
        # Add text
        draw = ImageDraw.Draw(img)
        
        # Try to use a system font or fall back to default
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 50)
        except:
            try:
                font = ImageFont.truetype("arial.ttf", 50)
            except:
                font = ImageFont.load_default()
        
        # Calculate text position
        bbox = draw.textbbox((0, 0), formatted_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (w - text_width) // 2
        y = (h - text_height) // 2
        
        # Draw text
        draw.text((x, y), formatted_text, font=font, fill="white", align="center")
        
        # Save to BytesIO
        output = io.BytesIO()
        if "sticker" in flags:
            output.name = "quote.webp"
            img.save(output, "WEBP")
        else:
            output.name = "quote.png"
            img.save(output, "PNG")
        output.seek(0)
        
        # Send the image
        if "sticker" in flags:
            await message.reply_sticker(output)
        else:
            await message.reply_photo(output)
            
        await status_msg.delete()
        
        # Clean up
        try:
            import os
            if os.path.exists(pfp_path):
                os.remove(pfp_path)
        except:
            pass
            
    except Exception as e:
        await status_msg.edit(f"<b>ERROR:</b> <i>Failed to create quote picture: {e}</i>")
        LOGGER.error(f"Quote pic error: {e}")


@bot.add_cmd(cmd=["q", "rq", "fq"])
async def quote_sticker(bot: BOT, message: Message):
    """Create quote stickers with various modes"""
    
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
    """Create a quote sticker using @QuotLyBot"""
    
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


@bot.add_cmd(cmd="quote")
async def simple_quote(bot: BOT, message: Message):
    """Create a simple text quote"""
    
    reply = message.reply_to_message
    text_input = " ".join(message.text.split()[1:]) if len(message.text.split()) > 1 else ""
    
    if not reply and not text_input:
        return await message.reply(
            "<b>Usage:</b>\n"
            "<code>quote</code> <i>[reply to message]</i>\n"
            "<code>quote [text]</code> <i>to create quote with custom text</i>"
        )
    
    # Get the text to quote
    if reply and reply.text:
        quote_text = reply.text
    elif text_input:
        quote_text = text_input
    else:
        return await message.reply("<b>ERROR:</b> <i>No text found to quote</i>")
    
    # Format the quote
    formatted_quote = f'<blockquote>"{quote_text}"</blockquote>'
    
    await message.reply(formatted_quote)
