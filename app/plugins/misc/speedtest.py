#!/usr/bin/env python3
from speedtest import Speedtest, ConfigRetrievalError
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
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    if i >= len(size_name):
        i = len(size_name) - 1
    
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"


@bot.add_cmd(cmd="speedtest")
async def speedtest_cmd(bot: BOT, message: Message):
    """Run a network speed test and display the results"""
    speed_msg = await message.reply("<i>Initiating Speedtest...</i>")
    
    try:
        test = Speedtest()
    except ConfigRetrievalError:
        await speed_msg.edit(
            "<b>ERROR:</b> <i>Can't connect to Server at the Moment, Try Again Later!</i>"
        )
        return
    
    try:
        # Get best server and run tests
        test.get_best_server()
        test.download()
        test.upload()
        test.results.share()
        result = test.results.dict()
        
        # Format the results
        string_speed = f"""
➲ <b><i>SPEEDTEST INFO</i></b>
┠ <b>Upload:</b> <code>{get_readable_file_size(result['upload'] / 8)}/s</code>
┠ <b>Download:</b> <code>{get_readable_file_size(result['download'] / 8)}/s</code>
┠ <b>Ping:</b> <code>{result['ping']} ms</code>
┠ <b>Time:</b> <code>{result['timestamp']}</code>
┠ <b>Data Sent:</b> <code>{get_readable_file_size(int(result['bytes_sent']))}</code>
┖ <b>Data Received:</b> <code>{get_readable_file_size(int(result['bytes_received']))}</code>

➲ <b><i>SPEEDTEST SERVER</i></b>
┠ <b>Name:</b> <code>{result['server']['name']}</code>
┠ <b>Country:</b> <code>{result['server']['country']}, {result['server']['cc']}</code>
┠ <b>Sponsor:</b> <code>{result['server']['sponsor']}</code>
┠ <b>Latency:</b> <code>{result['server']['latency']}</code>
┠ <b>Latitude:</b> <code>{result['server']['lat']}</code>
┖ <b>Longitude:</b> <code>{result['server']['lon']}</code>

➲ <b><i>CLIENT DETAILS</i></b>
┠ <b>IP Address:</b> <code>{result['client']['ip']}</code>
┠ <b>Latitude:</b> <code>{result['client']['lat']}</code>
┠ <b>Longitude:</b> <code>{result['client']['lon']}</code>
┠ <b>Country:</b> <code>{result['client']['country']}</code>
┠ <b>ISP:</b> <code>{result['client']['isp']}</code>
┖ <b>ISP Rating:</b> <code>{result['client']['isprating']}</code>
"""
        
        # Try to send with photo first, then fallback to text only
        photo_sent = False
        try:
            await message.reply_photo(photo=result["share"])
            await speed_msg.delete()
            photo_sent = True
        except Exception as photo_error:
            LOGGER.warning(f"Failed to send photo: {photo_error}")
            photo_sent = False
        
        # If photo failed, send as text message
        if not photo_sent:
            await speed_msg.edit(string_speed)
            
    except Exception as e:
        LOGGER.error(f"Speedtest error: {str(e)}")
        await speed_msg.edit(
            f"<b>ERROR:</b> <i>Failed to complete speedtest: {str(e)}</i>"
        )