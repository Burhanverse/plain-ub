import asyncio
import aiohttp
from base64 import b64decode
from io import BytesIO
import re
from urllib.parse import urlparse

from app import BOT, bot, Message


class SiteConfig:
    """Intelligent site configuration based on URL analysis"""
    
    # Heavy sites that need aggressive waiting and longer timeouts
    HEAVY_SITES = {
        'youtube.com', 'youtu.be', 'facebook.com', 'fb.com', 'reddit.com', 'redd.it',
        'twitter.com', 'x.com', 'instagram.com', 'linkedin.com', 'tiktok.com',
        'netflix.com', 'amazon.com', 'ebay.com', 'aliexpress.com', 'shopify.com',
        'discord.com', 'slack.com', 'teams.microsoft.com', 'zoom.us',
        'notion.so', 'figma.com', 'canva.com', 'miro.com', 'trello.com'
    }
    
    # Sites that work better in mobile view
    MOBILE_OPTIMIZED = {
        'instagram.com', 'tiktok.com', 'snapchat.com', 'whatsapp.com',
        'telegram.org', 'signal.org', 'pinterest.com'
    }
    
    # Sites that benefit from full page screenshots
    FULL_PAGE_SITES = {
        'github.com', 'gitlab.com', 'stackoverflow.com', 'stackexchange.com',
        'medium.com', 'dev.to', 'hashnode.com', 'codepen.io', 'jsfiddle.net',
        'news.ycombinator.com', 'lobste.rs', 'hackernews.org'
    }
    
    # News/article sites that need custom handling
    NEWS_SITES = {
        'bbc.com', 'cnn.com', 'reuters.com', 'ap.org', 'bloomberg.com',
        'techcrunch.com', 'theverge.com', 'arstechnica.com', 'wired.com',
        'wikipedia.org', 'wikimedia.org'
    }

    @staticmethod
    def analyze_url(url: str) -> dict:
        """Analyze URL and return optimal screenshot configuration"""
        try:
            parsed = urlparse(url.lower())
            domain = parsed.netloc.replace('www.', '').replace('m.', '')
            
            # Check for mobile subdomain
            is_mobile_url = parsed.netloc.startswith(('m.', 'mobile.'))
            
            config = {
                'aggressive_wait': False,
                'smart_wait': True,
                'wait_for_network_idle': True,
                'timeout': 30000,
                'extra_wait_time': 0,
                'mobile': is_mobile_url,
                'full_page': False,
                'format': 'png',
                'width': 1920,
                'height': 1080,
                'quality': None,
                'block_ads': True,
                'disable_animations': True,
                'delay': 1000
            }
            
            # Heavy sites configuration
            if any(site in domain for site in SiteConfig.HEAVY_SITES):
                config.update({
                    'aggressive_wait': True,
                    'timeout': 60000,
                    'extra_wait_time': 5000,
                    'delay': 3000,
                    'format': 'jpeg',
                    'quality': 85
                })
            
            # Mobile-optimized sites
            if any(site in domain for site in SiteConfig.MOBILE_OPTIMIZED) and not is_mobile_url:
                config.update({
                    'mobile': True,
                    'width': 375,
                    'height': 812
                })
            
            # Full page sites
            if any(site in domain for site in SiteConfig.FULL_PAGE_SITES):
                config.update({
                    'full_page': True,
                    'height': 1200  # Reasonable default for full page
                })
            
            # News sites optimization
            if any(site in domain for site in SiteConfig.NEWS_SITES):
                config.update({
                    'delay': 2000,
                    'extra_wait_time': 2000,
                    'width': 1200,
                    'height': 1000
                })
            
            # Special cases for common patterns
            if 'blog' in domain or 'docs' in domain:
                config.update({
                    'full_page': True,
                    'width': 1200
                })
            
            return config
            
        except Exception:
            # Fallback to default config
            return {
                'aggressive_wait': False,
                'smart_wait': True,
                'wait_for_network_idle': True,
                'timeout': 30000,
                'extra_wait_time': 0,
                'mobile': False,
                'full_page': False,
                'format': 'png',
                'width': 1920,
                'height': 1080,
                'quality': None,
                'block_ads': True,
                'disable_animations': True,
                'delay': 1000
            }


async def take_screenshot(url: str, retry_count: int = 0) -> tuple:
    """Take screenshot using WebSS API with intelligent configuration"""
    # Ensure URL has protocol
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    
    # Get intelligent configuration for this URL
    config = SiteConfig.analyze_url(url)
    
    payload = {
        "url": url,
        "width": config['width'],
        "height": config['height'],
        "format": config['format'],
        "full_page": config['full_page'],
        "mobile": config['mobile'],
        "output_format": "base64",
        "delay": config['delay'],
        "timeout": config['timeout'],
        "extra_wait_time": config['extra_wait_time'],
        "aggressive_wait": config['aggressive_wait'],
        "smart_wait": config['smart_wait'],
        "wait_for_network_idle": config['wait_for_network_idle'],
        "block_ads": config['block_ads'],
        "disable_animations": config['disable_animations']
    }
    
    # Add quality for JPEG
    if config['quality']:
        payload['quality'] = config['quality']
    
    try:
        timeout = aiohttp.ClientTimeout(total=max(90, config['timeout'] // 1000 + 30))
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://webss-latest.onrender.com/screenshot",
                json=payload,
                timeout=timeout
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success") and data.get("data"):
                        # Decode base64 image data
                        image_data = b64decode(data["data"])
                        file = BytesIO(image_data)
                        file.name = f"webss.{config['format']}"
                        return file, config, None
                    else:
                        error_msg = data.get('error', 'Screenshot failed')
                        return None, config, error_msg
                else:
                    return None, config, f"HTTP {response.status}"
                    
    except asyncio.TimeoutError:
        error_msg = "Screenshot timeout"
        # Retry with reduced settings for heavy sites
        if retry_count == 0 and config['aggressive_wait']:
            fallback_config = config.copy()
            fallback_config.update({
                'aggressive_wait': False,
                'timeout': 45000,
                'extra_wait_time': 0,
                'delay': 1000
            })
            return await take_screenshot_with_config(url, fallback_config), fallback_config, "Retried with faster settings"
        return None, config, error_msg
    except Exception as e:
        return None, config, str(e)


async def take_screenshot_with_config(url: str, config: dict):
    """Helper function to take screenshot with specific config"""
    payload = {
        "url": url,
        "width": config['width'],
        "height": config['height'],
        "format": config['format'],
        "full_page": config['full_page'],
        "mobile": config['mobile'],
        "output_format": "base64",
        "delay": config['delay'],
        "timeout": config['timeout'],
        "extra_wait_time": config['extra_wait_time'],
        "aggressive_wait": config['aggressive_wait'],
        "smart_wait": config['smart_wait'],
        "wait_for_network_idle": config['wait_for_network_idle'],
        "block_ads": config['block_ads'],
        "disable_animations": config['disable_animations']
    }
    
    if config.get('quality'):
        payload['quality'] = config['quality']
    
    try:
        timeout = aiohttp.ClientTimeout(total=max(60, config['timeout'] // 1000 + 15))
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://webss-latest.onrender.com/screenshot",
                json=payload,
                timeout=timeout
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success") and data.get("data"):
                        image_data = b64decode(data["data"])
                        file = BytesIO(image_data)
                        file.name = f"webss.{config['format']}"
                        return file
                return None
    except Exception:
        return None


@bot.add_cmd(cmd="ss")
async def take_ss(bot: BOT, message: Message):
    """Take intelligent website screenshot
    
    Automatically optimizes settings based on the website:
    - Heavy sites (YouTube, Facebook, etc.): Uses aggressive waiting
    - Mobile sites: Automatically uses mobile viewport
    - Code/docs sites: Takes full page screenshots
    - News sites: Optimized dimensions and timing
    """
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    # If no URL provided, try to extract from replied message
    if not args and message.reply_to_message:
        replied_text = message.reply_to_message.text or message.reply_to_message.caption or ""
        # Enhanced URL extraction from replied message
        url_pattern = r'https?://[^\s<>\'"]*[^\s<>\'".,;!?]'
        urls = re.findall(url_pattern, replied_text)
        if urls:
            args = [urls[0]]  # Use the first URL found
    
    if not args:
        return await message.reply(
            "<b>📸 WebSS - Smart Screenshot Tool</b>\n\n"
            "<b>Usage:</b> <code>ss [url]</code>\n\n"
            "<b>🧠 Smart Features:</b>\n"
            "• <i>Heavy sites</i> (YouTube, Facebook) → Aggressive waiting\n"
            "• <i>Mobile sites</i> (Instagram, TikTok) → Mobile viewport\n"
            "• <i>Code sites</i> (GitHub, docs) → Full page capture\n"
            "• <i>News sites</i> → Optimized dimensions\n\n"
            "<b>Examples:</b>\n"
            "<code>ss google.com</code>\n"
            "<code>ss youtube.com</code>\n"
            "<code>ss github.com/user/repo</code>\n\n"
            "<i>💡 Tip: Reply to a message with a URL using</i> <code>ss</code> <i>to auto-capture!</i>"
        )
    
    url = args[0].strip()
    
    # Clean up URL if needed
    if url.startswith(('<', '"', "'")):
        url = url[1:]
    if url.endswith(('>', '"', "'")):
        url = url[:-1]
    
    m = await message.reply("<code>🔍 Analyzing website...</code>")
    
    try:
        # Get intelligent configuration
        config = SiteConfig.analyze_url(url)
        
        # Update status based on detected configuration
        if config['aggressive_wait']:
            await m.edit("<code>🎯 Heavy site detected - Using aggressive mode...</code>")
        elif config['mobile']:
            await m.edit("<code>📱 Mobile-optimized site - Using mobile viewport...</code>")
        elif config['full_page']:
            await m.edit("<code>📄 Code/docs site - Capturing full page...</code>")
        else:
            await m.edit("<code>📸 Capturing screenshot...</code>")
        
        # Take screenshot with intelligent settings
        result, used_config, error = await take_screenshot(url)
        
        if not result:
            error_msg = f"<b>❌ ERROR:</b> <i>{error or 'Failed to capture screenshot'}</i>"
            if "timeout" in str(error).lower():
                error_msg += f"\n\n<i>💡 This site might be very slow. The WebSS API tried its best with {used_config['timeout']/1000:.0f}s timeout.</i>"
            return await m.edit(error_msg)
        
        await m.edit("<code>📤 Uploading screenshot...</code>")
        
        # Prepare caption with intelligent info
        site_type = "🌐"
        if used_config['aggressive_wait']:
            site_type = "🎯 Heavy Site"
        elif used_config['mobile']:
            site_type = "📱 Mobile View"
        elif used_config['full_page']:
            site_type = "📄 Full Page"
        
        caption = (
            f"<b>🌍 Website:</b> <code>{url}</code>\n"
            f"<b>📐 Size:</b> <code>{used_config['width']}x{used_config['height']}</code>\n"
            f"<b>🎨 Format:</b> <code>{used_config['format'].upper()}</code>\n"
            f"<b>🏷 Type:</b> <code>{site_type}</code>"
        )
        
        # Add timing info for heavy sites
        if used_config['aggressive_wait']:
            caption += f"\n<b>⏱ Timeout:</b> <code>{used_config['timeout']/1000:.0f}s</code>"
        
        # Send screenshot based on type and format
        photo, document = result, result
        
        if not used_config['full_page'] and used_config['format'] in ["png", "jpeg"]:
            # For normal screenshots, send both document and compressed photo
            tasks = []
            
            # Always send as document for full quality
            tasks.append(
                message.reply_document(
                    document, 
                    caption=caption + "\n\n<i>📎 Full quality version</i>"
                )
            )
            
            # Send compressed version as photo for quick preview
            photo.seek(0)
            if used_config['format'] in ["png", "jpeg"]:
                tasks.append(
                    message.reply_photo(
                        photo, 
                        caption=f"<i>🖼 Quick preview - see document for full quality</i>"
                    )
                )
            
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # For full page or other formats, send only as document
            await message.reply_document(
                document,
                caption=caption
            )
        
        await m.delete()
        
    except Exception as e:
        error_msg = f"<b>💥 UNEXPECTED ERROR:</b> <code>{str(e)}</code>"
        await m.edit(error_msg)