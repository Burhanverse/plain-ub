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
            
            if (parsed.netloc.startswith(('m.', 'mobile.', 'touch.')) or 
                'mobile' in path or '/m/' in path):
                config.update({
                    'mobile': True,
                    'width': 375,
                    'height': 812
                })
            
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
            
            news_patterns = ['news', 'cnn', 'bbc', 'reuters', 'bloomberg', 'techcrunch',
                           'theverge', 'arstechnica', 'medium', 'blog']
            if (any(pattern in domain for pattern in news_patterns) or 
                'blog' in domain or '/blog' in path or '/news' in path or 
                '/article' in path or '/post' in path):
                config.update({
                    'full_page': True,
                    'delay': 2000,
                    'extra_wait_time': 2000,
                    'width': 1200,
                    'height': 1000
                })
            
            full_page_paths = ['/docs', '/doc', '/documentation', '/guide', '/guides',
                             '/news', '/article', '/articles', '/post', '/posts',
                             '/blog', '/tutorial', '/tutorials', '/help', '/support',
                             '/wiki', '/knowledge', '/manual', '/readme']
            if any(pattern in path for pattern in full_page_paths):
                config.update({
                    'full_page': True,
                    'width': 1200,
                    'height': 1400,
                    'delay': 2000
                })
            
            spa_indicators = ['app', 'dashboard', 'admin', 'panel', 'console']
            if (any(indicator in domain for indicator in spa_indicators) or
                any(indicator in path for indicator in ['/app', '/dashboard', '/admin', '/panel'])):
                config.update({
                    'aggressive_wait': True,
                    'timeout': 50000,
                    'extra_wait_time': 4000,
                    'delay': 3000
                })
            
            finance_patterns = ['bank', 'financial', 'finance', 'pay', 'wallet', 'crypto']
            if any(pattern in domain for pattern in finance_patterns):
                config.update({
                    'timeout': 45000,
                    'extra_wait_time': 3000,
                    'delay': 2000,
                    'disable_animations': True
                })
            
            edu_patterns = ['edu', 'school', 'university', 'course', 'learn', 'tutorial']
            if (any(pattern in domain for pattern in edu_patterns) or
                domain.endswith('.edu')):
                config.update({
                    'full_page': True,
                    'width': 1200,
                    'height': 1200
                })
            
            cdn_patterns = ['cdn', 'static', 'assets', 's3', 'cloudfront']
            if any(pattern in domain for pattern in cdn_patterns):
                config.update({
                    'timeout': 15000,
                    'delay': 500,
                    'extra_wait_time': 0
                })
            
            if url.startswith('https://'):
                config['delay'] = max(config['delay'], 1500)
                config['delay'] = max(config['delay'], 1500)
            
            return config
            
        except Exception:
            return {
                'aggressive_wait': False,
                'smart_wait': True,
                'wait_for_network_idle': True,
                'timeout': 30000,
                'extra_wait_time': 2000,
                'mobile': False,
                'full_page': False,
                'format': 'png',
                'width': 1920,
                'height': 1080,
                'quality': None,
                'block_ads': True,
                'disable_animations': True,
                'delay': 1500
            }


async def take_screenshot(url: str, retry_count: int = 0) -> tuple:
    """Take screenshot using WebSS API with intelligent configuration"""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    
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
    """Take website screenshot with intelligent optimization"""
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if not args and message.reply_to_message:
        replied_text = message.reply_to_message.text or message.reply_to_message.caption or ""
        url_pattern = r'https?://[^\s<>\'"]*[^\s<>\'".,;!?]'
        urls = re.findall(url_pattern, replied_text)
        if urls:
            args = [urls[0]]
    
    if not args:
        return await message.reply(
            "<b>Usage:</b> <code>ss [url]</code>\n\n"
            "<b>Features:</b>\n"
            "• Social media sites - Aggressive loading for JS-heavy sites\n"
            "• Video platforms - Extra patience for streaming sites\n"
            "• Code platforms - Full page capture for repositories\n"
            "• E-commerce sites - Dynamic content loading\n"
            "• Mobile URLs - Automatic mobile viewport\n"
            "• News/blogs - Optimized article reading\n"
            "• Apps/dashboards - SPA-aware timing\n\n"
            "<b>Example:</b>\n"
            "<code>ss google.com</code>\n"
            "<i>Tip: Reply to a message containing a URL with just 'ss' to automatically screenshot it</i>"
        )
    
    url = args[0].strip()
    
    if url.startswith(('<', '"', "'")):
        url = url[1:]
    if url.endswith(('>', '"', "'")):
        url = url[:-1]
    
    m = await message.reply("<code>Analyzing website...</code>")
    
    try:
        config = IntelligentConfig.analyze_url(url)
        
        if config['aggressive_wait'] and config['timeout'] > 60000:
            await m.edit("<code>Video/streaming site detected - Using maximum patience mode...</code>")
        elif config['aggressive_wait']:
            await m.edit("<code>Dynamic site detected - Using enhanced loading...</code>")
        elif config['mobile']:
            await m.edit("<code>Mobile layout detected - Using mobile viewport...</code>")
        elif config['full_page']:
            await m.edit("<code>Documentation/code site - Capturing full content...</code>")
        else:
            await m.edit("<code>Standard site - Optimizing capture...</code>")
        
        result, used_config, error = await take_screenshot(url)
        
        if not result:
            error_msg = f"<b>ERROR:</b> <i>{error or 'Failed to capture screenshot'}</i>"
            if "timeout" in str(error).lower():
                error_msg += f"\n\n<i>This site might be very slow. The WebSS API tried its best with {used_config['timeout']/1000:.0f}s timeout.</i>"
            return await m.edit(error_msg)
        
        await m.edit("<code>Uploading screenshot...</code>")
        
        site_type = "Standard"
        if used_config['aggressive_wait'] and used_config['timeout'] > 60000:
            site_type = "Video Platform"
        elif used_config['aggressive_wait']:
            site_type = "Dynamic Site"
        elif used_config['mobile']:
            site_type = "Mobile Layout"
        elif used_config['full_page']:
            site_type = "Full Content"
        
        caption = (
            f"<b>Website:</b> <code>{url}</code>\n"
            f"<b>Size:</b> <code>{used_config['width']}x{used_config['height']}</code>\n"
            f"<b>Format:</b> <code>{used_config['format'].upper()}</code>\n"
            f"<b>Type:</b> <code>{site_type}</code>"
        )
        
        if used_config['aggressive_wait']:
            caption += f"\n<b>Timeout:</b> <code>{used_config['timeout']/1000:.0f}s</code>"
        
        photo, document = result, result
        
        if not used_config['full_page'] and used_config['format'] in ["png", "jpeg"]:
            tasks = []

            tasks.append(
                message.reply_document(
                    document, 
                    caption=caption + "\n\n<i>Full quality version</i>"
                )
            )
            
            photo.seek(0)
            if used_config['format'] in ["png", "jpeg"]:
                tasks.append(
                    message.reply_photo(
                        photo, 
                        caption="<i>Quick preview - see document for full quality</i>"
                    )
                )
            
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            await message.reply_document(
                document,
                caption=caption
            )
        
        await m.delete()
        
    except Exception as e:
        error_msg = f"<b>UNEXPECTED ERROR:</b> <code>{str(e)}</code>"
        await m.edit(error_msg)
