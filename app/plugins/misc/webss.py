import asyncio
import aiohttp
from base64 import b64decode
from io import BytesIO

from app import BOT, bot, Message


async def take_screenshot(url: str, full_page: bool = False, format: str = "png", width: int = 1920, height: int = 1080):
    """Take screenshot using WebSS API"""
    # Ensure URL has protocol
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    
    payload = {
        "url": url,
        "width": width,
        "height": height,
        "format": format,
        "full_page": full_page,
        "output_format": "base64",
        "delay": 1000,
        "timeout": 30000,
        "block_ads": True,
        "disable_animations": True
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://webss-latest.onrender.com/screenshot",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success") and data.get("data"):
                        # Decode base64 image data
                        image_data = b64decode(data["data"])
                        file = BytesIO(image_data)
                        file.name = f"webss.{format}"
                        return file
                return None
    except Exception:
        return None


@bot.add_cmd(cmd="ss")
async def take_ss(bot: BOT, message: Message):
    """Take website screenshot with various options
    
    Usage:
    - ss <url> - Take normal screenshot
    - ss <url> full - Take full page screenshot
    - ss <url> full png 1920 1080 - Custom settings with format and dimensions
    """
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    # If no URL provided, try to extract from replied message
    if not args and message.reply_to_message:
        replied_text = message.reply_to_message.text or message.reply_to_message.caption or ""
        # Simple URL extraction from replied message
        import re
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, replied_text)
        if urls:
            args = [urls[0]]  # Use the first URL found
    
    if not args:
        return await message.reply(
            "<b>Usage:</b>\n"
            "<code>ss [url]</code> <i>- Normal screenshot</i>\n"
            "<code>ss [url] full</code> <i>- Full page screenshot</i>\n"
            "<code>ss [url] full png 1920 1080</code> <i>- Custom settings</i>\n\n"
            "<b>Example:</b>\n"
            "<code>ss google.com</code>\n"
            "<code>ss google.com full</code>\n\n"
            "<i>💡 Tip: Reply to a message containing a URL with just</i> <code>ss</code> <i>to automatically screenshot it!</i>"
        )
    
    url = args[0]
    full_page = False
    format = "png"
    width = 1920
    height = 1080
    
    # Parse additional arguments
    if len(args) > 1:
        for i, arg in enumerate(args[1:], 1):
            if arg.lower() in ["full", "fullpage", "true", "yes", "1"]:
                full_page = True
            elif arg.lower() in ["png", "jpeg", "jpg", "webp"]:
                format = "jpeg" if arg.lower() == "jpg" else arg.lower()
            elif arg.isdigit():
                if i == len(args) - 1 or not args[i + 1].isdigit():
                    width = int(arg)
                else:
                    width = int(arg)
                    if i + 1 < len(args) and args[i + 1].isdigit():
                        height = int(args[i + 1])
    
    # Validate dimensions
    width = max(320, min(3840, width))
    height = max(240, min(2160, height))
    
    m = await message.reply("<code>Capturing screenshot...</code>")
    
    try:
        photo = await take_screenshot(url, full_page, format, width, height)
        
        if not photo:
            return await m.edit("<b>ERROR:</b> <i>Failed to take screenshot. Please check the URL and try again.</i>")
        
        await m.edit("<code>Uploading screenshot...</code>")
        
        # Send both document and photo for better user experience
        if not full_page and format in ["png", "jpeg"]:
            # For normal screenshots, send both document and photo
            tasks = [
                message.reply_document(
                    photo, 
                    caption=f"<b>Website:</b> <code>{url}</code>\n<b>Size:</b> <code>{width}x{height}</code>\n<b>Format:</b> <code>{format.upper()}</code>"
                ),
            ]
            # Reset file pointer for photo
            photo.seek(0)
            if format in ["png", "jpeg"]:
                tasks.append(message.reply_photo(photo))
            
            await asyncio.gather(*tasks)
        else:
            # For full page screenshots, send only as document
            await message.reply_document(
                photo,
                caption=f"<b>Website:</b> <code>{url}</code>\n<b>Size:</b> <code>{width}x{height}</code> (Full Page)\n<b>Format:</b> <code>{format.upper()}</code>"
            )
        
        await m.delete()
        
    except Exception as e:
        await m.edit(f"<b>ERROR:</b> <i>{str(e)}</i>")