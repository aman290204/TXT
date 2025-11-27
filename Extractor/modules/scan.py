import asyncio
import json
import os
import re
import time
import aiohttp
from pyrogram import filters, Client
from Extractor import app
from config import PREMIUM_LOGS, BOT_TEXT

# File to store scan progress
PROGRESS_FILE = "scan_progress.json"

class ScanState:
    def __init__(self):
        self.is_scanning = False
        self.current_code = "aa"  # Start from 2 letters
        self.found_orgs = []
        self.start_time = 0
        self.scanned_count = 0
        self.load()

    def save(self):
        data = {
            "current_code": self.current_code,
            "found_orgs": self.found_orgs,
            "scanned_count": self.scanned_count
        }
        with open(PROGRESS_FILE, "w") as f:
            json.dump(data, f)

    def load(self):
        if os.path.exists(PROGRESS_FILE):
            try:
                with open(PROGRESS_FILE, "r") as f:
                    data = json.load(f)
                    self.current_code = data.get("current_code", "aa")
                    self.found_orgs = data.get("found_orgs", [])
                    self.scanned_count = data.get("scanned_count", 0)
            except Exception as e:
                print(f"Error loading progress: {e}")

scan_state = ScanState()

# Detect if running on Render/cloud or locally
IS_CLOUD = os.environ.get('RENDER') or os.environ.get('DYNO')

# Semaphore to limit concurrent org processing
# Conservative for cloud (512MB limit), aggressive for local
processing_semaphore = asyncio.Semaphore(2 if IS_CLOUD else 10)
# Semaphore to limit concurrent folder fetching within a batch
folder_semaphore = asyncio.Semaphore(5 if IS_CLOUD else 50)

print(f"[INIT] Running in {'CLOUD' if IS_CLOUD else 'LOCAL'} mode")
print(f"[INIT] Processing semaphore: {2 if IS_CLOUD else 10}")
print(f"[INIT] Folder semaphore: {5 if IS_CLOUD else 50}")

def next_code(code):
    """Generate the next org code (variable length: aa -> ab -> ... -> zz -> aaa -> ...)."""
    chars = list(code)
    i = len(chars) - 1
    
    while i >= 0:
        if chars[i] == 'z':
            chars[i] = 'a'
            i -= 1
        else:
            chars[i] = chr(ord(chars[i]) + 1)
            return "".join(chars)
    
    # If we overflow (all z's), add a new character
    return 'a' * (len(chars) + 1)

async def check_org_validity(session, org_code):
    """Check if an org code is valid using the Classplus API."""
    url = f"https://api.classplusapp.com/v2/orgs/{org_code}"
    headers = {
        'user-agent': 'Mobile-Android',
        'app-version': '1.4.65.3',
        'api-version': '29',
        'device-id': '39F093FF35F201D9'
    }
    try:
        async with session.get(url, headers=headers, timeout=10) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("status") == "success" and data.get("data"):
                    org_data = data["data"]
                    org_name = org_data.get("orgName", "Unknown")
                    
                    # Try to fetch store hash for content extraction
                    store_url = f"https://{org_code}.courses.store"
                    try:
                        async with session.get(store_url, timeout=10) as store_response:
                            if store_response.status == 200:
                                text = await store_response.text()
                                hash_match = re.search(r'"hash":"(.*?)"', text)
                                if hash_match:
                                    return True, hash_match.group(1), org_name
                    except:
                        pass
                    
                    # Valid org even if hash not found
                    return True, None, org_name
            return False, None, None
    except Exception as e:
        return False, None, None

async def fetch_store_batches(session, token):
    """Fetch ALL batches using the store token with pagination."""
    if not token:
        return []
    
    headers = {
        "api-version": "35",
        "app-version": "1.4.73.2",
        "device-id": "scanner_bot",
        "region": "IN",
    }
    
    all_batches = []
    page = 0
    
    while True:
        url = f"https://api.classplusapp.com/v2/course/preview/similar/{token}?limit=100&page={page}"
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    batches = data.get("data", {}).get("coursesData", [])
                    
                    if not batches:
                        break
                    
                    all_batches.extend(batches)
                    page += 1
                    
                    if len(batches) < 100:
                        break
                else:
                    break
        except Exception as e:
            print(f"Error fetching batches page {page}: {e}")
            break
    
    return all_batches

async def fetch_batch_content(session, batch_token, file_handle, folder_id=0, folder_path=""):
    """Recursively fetch content for a batch and write to file."""
    url = f"https://api.classplusapp.com/v2/course/preview/content/list/{batch_token}"
    params = {'folderId': folder_id, 'limit': 9999}
    headers = {
        "api-version": "35",
        "app-version": "1.4.73.2",
        "device-id": "scanner_bot",
        "region": "IN",
    }
    
    count = 0
    try:
        # Limit concurrent folder fetches
        async with folder_semaphore:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    items = data.get("data", [])
                    
                    tasks = []
                    for item in items:
                        if item.get("contentType") == 1:  # Folder
                            folder_name = item.get("name", "Untitled")
                            new_path = f"{folder_path}({folder_name})"
                            tasks.append(fetch_batch_content(session, batch_token, file_handle, item.get("id"), new_path))
                        else:
                            name = item.get("name", "Untitled")
                            
                            # Try to find the ID from various possible fields
                            video_id = item.get("contentHashId") or item.get("hash") or item.get("videoId")
                            thumbnail_url = item.get("thumbnailUrl", "")
                            
                            url_val = None
                            
                            # Logic 1: Check if thumbnail has /cc/ pattern (New DRM)
                            if "/cc/" in thumbnail_url:
                                base_url = thumbnail_url.rsplit('/', 1)[0]
                                url_val = f"{base_url}/master.m3u8"
                            
                            # Logic 2: Check if thumbnail has /drm/wv/ pattern (Widevine DRM)
                            elif "/drm/wv/" in thumbnail_url:
                                base_url = thumbnail_url.rsplit('/', 1)[0]
                                url_val = f"{base_url}/master.m3u8"
                                
                            # Logic 3: Use explicit video ID if found (and not handled by above)
                            elif video_id and not url_val:
                                url_val = f"https://media-cdn.classplusapp.com/drm/{video_id}/playlist.m3u8"
                                
                            # Logic 4: Fallback to existing URL or thumbnail
                            if not url_val:
                                url_val = item.get("url") or thumbnail_url
                                
                            if url_val:
                                # Write directly to file
                                file_handle.write(f"{folder_path}{name}:{url_val}\n")
                                count += 1
                    
                    if tasks:
                        sub_counts = await asyncio.gather(*tasks)
                        count += sum(sub_counts)
    except Exception as e:
        print(f"Error fetching content: {e}")
        
    return count

async def process_valid_org(client, message, org_code, token, org_name):
    """Process a valid org: fetch batches, extract content, send files."""
    # Use semaphore to limit concurrent processing and prevent memory overflow
    async with processing_semaphore:
        try:
            print(f"[PROCESS] Starting to process org: {org_code} ({org_name})")
            # Create own session since this runs as background task
            async with aiohttp.ClientSession() as session:
                # Add timeout for fetching batches (30 seconds max)
                try:
                    batches = await asyncio.wait_for(
                        fetch_store_batches(session, token),
                        timeout=30.0
                    )
                except asyncio.TimeoutError:
                    print(f"[PROCESS ERROR] Timeout fetching batches for {org_code}")
                    await client.send_message(
                        message.chat.id,
                        f"⚠️ **Timeout processing org: {org_code}**\n"
                        f"📛 **Name:** {org_name}"
                    )
                    return
                
                if not batches:
                    print(f"[PROCESS] No batches found for {org_code}")
                    await client.send_message(
                        message.chat.id,
                        f"✅ **Valid Org: {org_code}**\n"
                        f"📛 **Name:** {org_name}\n"
                        f"⚠️ No public batches found"
                    )
                    if PREMIUM_LOGS:
                        await client.send_message(PREMIUM_LOGS, f"✅ Valid Org: {org_code} ({org_name}) - No batches")
                    return
                
                print(f"[PROCESS] Found {len(batches)} batches for {org_code}")
                await client.send_message(
                    message.chat.id, 
                    f"🎯 **Valid Org Found!**\n"
                    f"📛 **Name:** {org_name}\n"
                    f"🔤 **Code:** {org_code}\n"
                    f"📚 **Batches:** {len(batches)}\n"
                    f"⏳ Extracting content..."
                )

                for batch in batches:
                    batch_name = batch.get("name", "Unknown Batch")
                    batch_id = batch.get("id")
                    print(f"[DEBUG] Processing batch: {batch_name} (ID: {batch_id})")
                    
                    # Get batch token for content extraction
                    info_url = "https://api.classplusapp.com/v2/course/preview/org/info"
                    info_params = {'courseId': batch_id}
                    info_headers = {
                        "api-version": "22",
                        "tutorWebsiteDomain": f"https://{org_code}.courses.store"
                    }
                    
                    batch_token = None
                    try:
                        async with session.get(info_url, params=info_params, headers=info_headers, timeout=10) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                batch_token = data.get("data", {}).get("hash")
                                print(f"[DEBUG] Got batch token for {batch_name}: {batch_token}")
                            else:
                                print(f"[DEBUG] Failed to get batch token. Status: {resp.status}")
                    except Exception as e:
                        print(f"[PROCESS ERROR] Failed to get batch token for {batch_name} in {org_code}: {e}")
                        continue
                    
                    if batch_token:
                        filename = f"{org_name}_{batch_name}_{org_code}.txt".replace("/", "-").replace(":", "-")
                        
                        # Pass batch name as the root folder
                        # Stream content directly to file to save memory
                        total_links = 0
                        try:
                            print(f"[DEBUG] Starting content fetch for {batch_name}...")
                            with open(filename, "w", encoding="utf-8") as f:
                                # Add timeout for content extraction (600 seconds max per batch)
                                total_links = await asyncio.wait_for(
                                    fetch_batch_content(session, batch_token, f, folder_path=f"({batch_name})"),
                                    timeout=600.0
                                )
                            print(f"[PROCESS] Extracted {total_links} links from {batch_name} in {org_code}")
                        except asyncio.TimeoutError:
                            print(f"[PROCESS ERROR] Timeout extracting content for {batch_name} in {org_code}")
                            if os.path.exists(filename):
                                os.remove(filename)
                            continue
                        except Exception as e:
                            print(f"[PROCESS ERROR] Error writing file {filename}: {e}")
                            if os.path.exists(filename):
                                os.remove(filename)
                            continue

                        if total_links > 0:
                            caption = (
                                f"🎓 **ORG EXTRACTED**\n"
                                f"🏢 **Org:** {org_name} ({org_code})\n"
                                f"📚 **Batch:** {batch_name}\n"
                                f"🔗 **Links:** {total_links}\n"
                                f"🤖 {BOT_TEXT}"
                            )
                            
                            try:
                                print(f"[DEBUG] Sending file {filename}...")
                                await client.send_document(message.chat.id, filename, caption=caption)
                                print(f"[PROCESS] Sent file for {batch_name} in {org_code}")
                                if PREMIUM_LOGS:
                                    await client.send_document(PREMIUM_LOGS, filename, caption=caption)
                            except Exception as e:
                                print(f"[PROCESS ERROR] Error sending file {filename}: {e}")
                            finally:
                                if os.path.exists(filename):
                                    os.remove(filename)
                        else:
                            print(f"[DEBUG] No links found for {batch_name}, deleting empty file.")
                            # Clean up empty file
                            if os.path.exists(filename):
                                os.remove(filename)
                    else:
                        print(f"[DEBUG] No batch token found for {batch_name}")
                
                print(f"[PROCESS] Completed processing org: {org_code}")
        except Exception as e:
            print(f"[PROCESS ERROR] Unexpected error processing org {org_code}: {e}")
            import traceback
            traceback.print_exc()

async def scanner_loop(client, message):
    scan_state.start_time = time.time()
    
    await message.reply_text(
        f"🚀 **Scanner Started**\n"
        f"📍 Starting from: `{scan_state.current_code}`\n"
        f"ℹ️ Use /scan_status to check progress"
    )
    
    async with aiohttp.ClientSession() as session:
        while scan_state.is_scanning:
            code = scan_state.current_code
            
            is_valid, token, org_name = await check_org_validity(session, code)
            
            scan_state.scanned_count += 1
            
            if is_valid:
                scan_state.found_orgs.append(code)
                scan_state.save()
                print(f"[SCAN] Valid org found: {code} ({org_name})")
                
                # Wait if too many orgs are being processed to prevent backlog
                # This ensures the sender keeps up with the scanner
                if processing_semaphore.locked():
                    print(f"[SCAN] Too many orgs processing, waiting...")
                    await processing_semaphore.acquire()
                    processing_semaphore.release()
                
                # Run org processing in background so scanner doesn't block
                # Wrap in error handler to prevent silent crashes
                task = asyncio.create_task(process_valid_org(client, message, code, token, org_name))
                task.add_done_callback(lambda t: print(f"[TASK ERROR] {t.exception()}") if t.exception() else None)
            
            scan_state.current_code = next_code(code)
            
            if scan_state.scanned_count % 10 == 0:
                scan_state.save()
            
            # Reduced delay for faster scanning on powerful local machines
            await asyncio.sleep(0.1)

    await message.reply_text("🛑 **Scanner Stopped**")

@app.on_message(filters.command("scan_org"))
async def start_scan(client, message):
    try:
        print(f"[SCAN] Command received from user {message.from_user.id}")
        
        if scan_state.is_scanning:
            await message.reply_text("⚠️ Scanner is already running!")
            return
        
        args = message.command
        if len(args) > 1:
            start_code = args[1]
            if start_code.isalpha() and len(start_code) >= 2:
                scan_state.current_code = start_code.lower()
                print(f"[SCAN] Starting from custom code: {scan_state.current_code}")
            else:
                await message.reply_text("⚠️ Invalid start code (must be 2+ letters). Using saved/default code.")
                print(f"[SCAN] Invalid start code: {start_code}")
        else:
            print(f"[SCAN] Starting from default/saved code: {scan_state.current_code}")
        
        scan_state.is_scanning = True
        asyncio.create_task(scanner_loop(client, message))
        print(f"[SCAN] Scanner task created successfully")
    except Exception as e:
        print(f"[SCAN ERROR] {e}")
        import traceback
        traceback.print_exc()
        await message.reply_text(f"❌ Error starting scanner: {str(e)}")

@app.on_message(filters.command("stop_scan"))
async def stop_scan(client, message):
    if not scan_state.is_scanning:
        await message.reply_text("⚠️ Scanner is not running.")
        return
    
    scan_state.is_scanning = False
    scan_state.save()
    await message.reply_text("🛑 Stopping scanner... (finishing current task)")

@app.on_message(filters.command("scan_status"))
async def status_scan(client, message):
    duration = time.time() - scan_state.start_time if scan_state.is_scanning else 0
    status = "Running 🟢" if scan_state.is_scanning else "Stopped 🔴"
    
    text = (
        f"📊 **Scanner Status**\n\n"
        f"Status: {status}\n"
        f"Current Code: `{scan_state.current_code}`\n"
        f"Scanned: {scan_state.scanned_count}\n"
        f"Found: {len(scan_state.found_orgs)}\n"
        f"Duration: {int(duration)}s\n\n"
        f"Found Orgs: {', '.join(scan_state.found_orgs[-10:])}"
    )
    await message.reply_text(text)

@app.on_message(filters.command("test_scan"))
async def test_scan_module(client, message):
    """Test if scan module is loaded and responding."""
    await message.reply_text(
        "✅ **Scan Module Loaded**\n\n"
        f"Scanner is: {'Running 🟢' if scan_state.is_scanning else 'Stopped 🔴'}\n"
        f"Current code: `{scan_state.current_code}`\n"
        f"Commands available: /scan_org, /stop_scan, /scan_status"
    )
