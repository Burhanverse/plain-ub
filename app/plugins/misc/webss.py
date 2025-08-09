import asyncio
import aiohttp
from base64 import b64decode
from io import BytesIO
import re
from urllib.parse import urlparse

from app import BOT, bot, Message


class IntelligentConfig:
    """Dynamic configuration based on URL patterns and heuristics"""
    
    @staticmethod
    def analyze_url(url: str) -> dict:
        """Dynamically analyze URL and return optimal screenshot configuration"""
        try:
            parsed = urlparse(url.lower())
            domain = parsed.netloc.replace('www.', '').replace('m.', '')
            path = parsed.path.lower()
            
            # Start with smart defaults
            config = {
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
            
            # Mobile detection from URL patterns
            if (parsed.netloc.startswith(('m.', 'mobile.', 'touch.')) or 
                'mobile' in path or '/m/' in path):
                config.update({
                    'mobile': True,
                    'width': 375,
                    'height': 812
                })
            
            # Social media patterns (heavy JS, need aggressive wait)
            social_patterns = ['facebook', 'instagram', 'twitter', 'tiktok', 'youtube', 
                             'linkedin', 'snapchat', 'discord', 'telegram', 'whatsapp']
            if any(pattern in domain for pattern in social_patterns):
                config.update({
                    'aggressive_wait': True,
                    'timeout': 60000,
                    'extra_wait_time': 5000,
                    'delay': 3000,
                    'format': 'jpeg',
                    'quality': 85
                })
            
            # Video/streaming platforms (very heavy)
            video_patterns = ['youtube', 'netflix', 'twitch', 'vimeo', 'dailymotion']
            if any(pattern in domain for pattern in video_patterns):
                config.update({
                    'aggressive_wait': True,
                    'timeout': 70000,
                    'extra_wait_time': 8000,
                    'delay': 5000,
                    'format': 'jpeg',
                    'quality': 80
                })
            
            # E-commerce sites (dynamic content)
            ecommerce_patterns = ['shop', 'store', 'buy', 'cart', 'amazon', 'ebay', 
                                'aliexpress', 'etsy', 'shopify']
            if (any(pattern in domain for pattern in ecommerce_patterns) or 
                any(pattern in path for pattern in ['/shop', '/store', '/buy', '/cart'])):
                config.update({
                    'aggressive_wait': True,
                    'timeout': 45000,
                    'extra_wait_time': 3000,
                    'delay': 2000
                })
            
            # Developer/code platforms (good for full page)
            code_patterns = ['github', 'gitlab', 'bitbucket', 'codepen', 'jsfiddle', 
                           'replit', 'codesandbox', 'stackoverflow', 'stackexchange']
            if (any(pattern in domain for pattern in code_patterns) or 
                'docs' in domain or 'doc.' in domain or 
                any(pattern in path for pattern in ['/docs', '/doc', '/api', '/wiki'])):
                config.update({
                    'full_page': True,
                    'width': 1200,
                    'height': 1400,
                    'delay': 2000
                })
            
            # News and media sites
            news_patterns = ['news', 'cnn', 'bbc', 'reuters', 'bloomberg', 'techcrunch',
                           'theverge', 'arstechnica', 'medium', 'blog']
            if (any(pattern in domain for pattern in news_patterns) or 
                'blog' in domain or '/blog' in path or '/news' in path or 
                '/article' in path or '/post' in path):
                config.update({
                    'delay': 2000,
                    'extra_wait_time': 2000,
                    'width': 1200,
                    'height': 1000
                })
            
            # SPA (Single Page Applications) indicators - need more wait time
            spa_indicators = ['app', 'dashboard', 'admin', 'panel', 'console']
            if (any(indicator in domain for indicator in spa_indicators) or
                any(indicator in path for indicator in ['/app', '/dashboard', '/admin', '/panel'])):
                config.update({
                    'aggressive_wait': True,
                    'timeout': 50000,
                    'extra_wait_time': 4000,
                    'delay': 3000
                })
            
            # Banking/financial sites (usually heavy and secure)
            finance_patterns = ['bank', 'financial', 'finance', 'pay', 'wallet', 'crypto']
            if any(pattern in domain for pattern in finance_patterns):
                config.update({
                    'timeout': 45000,
                    'extra_wait_time': 3000,
                    'delay': 2000,
                    'disable_animations': True
                })
            
            # Educational platforms
            edu_patterns = ['edu', 'school', 'university', 'course', 'learn', 'tutorial']
            if (any(pattern in domain for pattern in edu_patterns) or
                domain.endswith('.edu')):
                config.update({
                    'full_page': True,
                    'width': 1200,
                    'height': 1200
                })
            
            # CDN or static sites (usually fast)
            cdn_patterns = ['cdn', 'static', 'assets', 's3', 'cloudfront']
            if any(pattern in domain for pattern in cdn_patterns):
                config.update({
                    'timeout': 15000,
                    'delay': 500,
                    'extra_wait_time': 0
                })
            
            # Localhost and development
            if 'localhost' in domain or domain.startswith('127.0.0.1') or domain.startswith('192.168.'):
                config.update({
                    'timeout': 20000,
                    'delay': 1000,
                    'block_ads': False  # Dev sites usually don't have ads
                })
            
            # HTTPS vs HTTP heuristic (HTTPS sites might be slower to establish connection)
            if url.startswith('https://'):
                config['delay'] = max(config['delay'], 1500)
            
            return config
            
        except Exception:
            # Fallback to safe defaults that work for most sites
            return {
                'aggressive_wait': False,
                'smart_wait': True,
                'wait_for_network_idle': True,
                'timeout': 30000,
                'extra_wait_time': 2000,  # Slightly more conservative
                'mobile': False,
                'full_page': False,
                'format': 'png',
                'width': 1920,
                'height': 1080,
                'quality': None,
                'block_ads': True,
                'disable_animations': True,
                'delay': 1500  # Slightly more conservative
            }


async def take_screenshot(url: str, retry_count: int = 0) -> tuple:
    """Take screenshot using WebSS API with intelligent configuration"""
    # Ensure URL has protocol
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    
    # Get intelligent configuration for this URL
    config = IntelligentConfig.analyze_url(url)
    
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
            "<b>📸 WebSS - Dynamic Screenshot Tool</b>\n\n"
            "<b>Usage:</b> <code>ss [url]</code>\n\n"
            "<b>� AI Features:</b>\n"
            "• <i>Social media</i> → Aggressive loading for JS-heavy sites\n"
            "• <i>Video platforms</i> → Extra patience for streaming sites\n"
            "• <i>Code platforms</i> → Full page capture for repositories\n"
            "• <i>E-commerce</i> → Dynamic content loading\n"
            "• <i>Mobile URLs</i> → Automatic mobile viewport\n"
            "• <i>News/blogs</i> → Optimized article reading\n"
            "• <i>Apps/dashboards</i> → SPA-aware timing\n\n"
            "<b>Examples:</b>\n"
            "<code>ss google.com</code>\n"
            "<code>ss any-website.com</code>\n"
            "<code>ss localhost:3000</code>\n\n"
            "<i>💡 Works intelligently with ANY website!</i>"
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
        config = IntelligentConfig.analyze_url(url)
        
        # Update status based on detected configuration
        if config['aggressive_wait'] and config['timeout'] > 60000:
            await m.edit("<code>📺 Video/streaming site detected - Maximum patience mode...</code>")
        elif config['aggressive_wait']:
            await m.edit("<code>⚡ Dynamic site detected - Using enhanced loading...</code>")
        elif config['mobile']:
            await m.edit("<code>📱 Mobile layout detected - Using mobile viewport...</code>")
        elif config['full_page']:
            await m.edit("<code>📄 Documentation/code site - Capturing full content...</code>")
        else:
            await m.edit("<code>📸 Standard site - Optimizing capture...</code>")
        
        # Take screenshot with intelligent settings
        result, used_config, error = await take_screenshot(url)
        
        if not result:
            error_msg = f"<b>❌ ERROR:</b> <i>{error or 'Failed to capture screenshot'}</i>"
            if "timeout" in str(error).lower():
                error_msg += f"\n\n<i>💡 This site might be very slow. The WebSS API tried its best with {used_config['timeout']/1000:.0f}s timeout.</i>"
            return await m.edit(error_msg)
        
        await m.edit("<code>📤 Uploading screenshot...</code>")
        
        # Prepare caption with intelligent info
        site_type = "🌐 Standard"
        if used_config['aggressive_wait'] and used_config['timeout'] > 60000:
            site_type = "📺 Video Platform"
        elif used_config['aggressive_wait']:
            site_type = "⚡ Dynamic Site"
        elif used_config['mobile']:
            site_type = "📱 Mobile Layout"
        elif used_config['full_page']:
            site_type = "📄 Full Content"
        
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