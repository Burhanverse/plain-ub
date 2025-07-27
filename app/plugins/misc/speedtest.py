from speedtest import Speedtest, ConfigRetrievalError
import math
from app import BOT, bot, Message, LOGGER


def get_readable_file_size(size_bytes):
    """Convert bytes to human readable format"""
    if size_bytes == 0:
        return "0B"
    
    size_name = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
    
    # Convert to int if it's a float, and handle the calculation properly
    size_bytes = abs(int(size_bytes))
    
    if size_bytes == 0:
        return "0B"
    
    # Calculate the appropriate unit
    i = int(math.floor(math.log(size_bytes, 1024)))
    if i >= len(size_name):
        i = len(size_name) - 1
    
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"


@bot.add_cmd(cmd="speedtest")
async def speedtest_cmd(bot: BOT, message: Message):
    """Run a network speed test and display the results
    
    Usage:
    - speedtest - Show results in text format
    - speedtest -i - Show results with image
    """
    
    # Check for image flag
    parts = message.text.split()
    send_image = len(parts) > 1 and "-i" in parts[1:]
    
    speed_msg = await message.reply("<code>Running speedtest...</code>")
    
    try:
        test = Speedtest()
    except ConfigRetrievalError:
        await speed_msg.edit(
            "<b>ERROR:</b> <i>Can't connect to speedtest servers, try again later</i>"
        )
        return
    
    try:
        # Update progress with different messages to avoid MESSAGE_NOT_MODIFIED error
        await speed_msg.edit("<code>Finding best server...</code>")
        test.get_best_server()
        
        await speed_msg.edit("<code>Testing download speed...</code>")
        test.download()
        
        await speed_msg.edit("<code>Testing upload speed...</code>")
        test.upload()
        
        if send_image:
            await speed_msg.edit("<code>Generating results image...</code>")
            test.results.share()
        else:
            await speed_msg.edit("<code>Processing results...</code>")
        
        result = test.results.dict()
        
        # Format the results with PLAIN UB style
        speed_text = f"""<b>SPEEDTEST RESULTS</b>

<b>Speed Test:</b>
• <b>Download:</b> <code>{get_readable_file_size(result['download'] / 8)}/s</code>
• <b>Upload:</b> <code>{get_readable_file_size(result['upload'] / 8)}/s</code>
• <b>Ping:</b> <code>{result['ping']} ms</code>

<b>Server Info:</b>
• <b>Server:</b> <code>{result['server']['name']}</code>
• <b>Location:</b> <code>{result['server']['country']}, {result['server']['cc']}</code>
• <b>Sponsor:</b> <code>{result['server']['sponsor']}</code>
• <b>Latency:</b> <code>{result['server']['latency']} ms</code>

<b>Client Info:</b>
• <b>ISP:</b> <code>{result['client']['isp']}</code>
• <b>IP:</b> <code>{result['client']['ip']}</code>
• <b>Location:</b> <code>{result['client']['country']}</code>

<b>Data Usage:</b>
• <b>Sent:</b> <code>{get_readable_file_size(int(result['bytes_sent']))}</code>
• <b>Received:</b> <code>{get_readable_file_size(int(result['bytes_received']))}</code>
• <b>Time:</b> <code>{result['timestamp']}</code>"""
        
        if send_image:
            # Send image with caption
            try:
                await message.reply_photo(
                    photo=result["share"], 
                    caption=speed_text
                )
                # Delete the status message after successful photo send
                try:
                    await speed_msg.delete()
                except Exception:
                    pass  # Ignore delete errors
            except Exception as photo_error:
                LOGGER.warning(f"Failed to send image: {photo_error}")
                try:
                    await speed_msg.edit(
                        f"{speed_text}\n\n<b>Note:</b> <i>Image generation failed, showing text results</i>"
                    )
                except Exception:
                    # Fallback: send as new message if edit fails
                    await message.reply(
                        f"{speed_text}\n\n<b>Note:</b> <i>Image generation failed, showing text results</i>"
                    )
        else:
            # Send text only
            try:
                await speed_msg.edit(speed_text)
            except Exception:
                # Fallback: send as new message if edit fails
                await message.reply(speed_text)
                try:
                    await speed_msg.delete()
                except Exception:
                    pass
            
    except Exception as e:
        LOGGER.error(f"Speedtest error: {str(e)}")
        error_msg = f"<b>ERROR:</b> <i>Speedtest failed: {str(e)}</i>"
        try:
            await speed_msg.edit(error_msg)
        except Exception:
            # Fallback: send as new message if edit fails
            await message.reply(error_msg)
            try:
                await speed_msg.delete()
            except Exception:
                pass