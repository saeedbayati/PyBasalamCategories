import asyncio
from basalam_sdk import BasalamClient, PersonalToken

# 📌 جای مشخص برای وارد کردن توکن خودتون
TOKEN = ""
REFRESH_TOKEN = ""

auth = PersonalToken(
    token=TOKEN,
    refresh_token=REFRESH_TOKEN
)
client = BasalamClient(auth=auth)

async def list_all_categories():
    categories = await client.core.get_categories()

    print("📋 لیست تمام دسته‌بندی‌ها و IDها:")
    for cat in categories:
        # اگر پاسخ tuple باشه
        cat_id, cat_title = cat  # unpack کردن tuple
        print(f"ID: {cat_id} | نام: {cat_title}")

# اجرای تابع
asyncio.run(list_all_categories())
