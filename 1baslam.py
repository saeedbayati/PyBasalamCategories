import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from basalam_sdk import BasalamClient, PersonalToken

class JSONSerializer(json.JSONEncoder):
    """کلاس کمکی برای سریال‌سازی آبجکت‌های غیرقابل سریال‌سازی"""
    def default(self, obj):
        try:
            # اگر آبجکت قابل سریال‌سازی مستقیم نیست، آن را به دیکشنری تبدیل کن
            if hasattr(obj, '__dict__'):
                # تبدیل به دیکشنری و حذف ویژگی‌های خصوصی
                result = {}
                for key, value in obj.__dict__.items():
                    if not key.startswith('_'):
                        result[key] = value
                return result
            elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
                return list(obj)
            else:
                return str(obj)
        except:
            return str(obj)

class CategoryExporter:
    """کلاس برای استخراج و ذخیره‌سازی دسته‌بندی‌ها به صورت JSON"""

    def __init__(self, token: str, refresh_token: str):
        self.auth = PersonalToken(
            token=token,
            refresh_token=refresh_token
        )
        self.client = BasalamClient(auth=self.auth)

    def safe_serialize(self, obj):
        """تبدیل ایمن هر آبجکتی به فرمت قابل سریال‌سازی"""
        if obj is None:
            return None
        elif isinstance(obj, (str, int, float, bool)):
            return obj
        elif isinstance(obj, dict):
            return {k: self.safe_serialize(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self.safe_serialize(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            # تبدیل آبجکت به دیکشنری
            result = {}
            for key, value in obj.__dict__.items():
                if not key.startswith('_'):  # نادیده گرفتن متغیرهای خصوصی
                    result[key] = self.safe_serialize(value)
            return result
        else:
            # برای هر نوع دیگر، به رشته تبدیل کن
            return str(obj)

    def extract_category_info(self, category) -> Dict[str, Any]:
        """استخراج اطلاعات از آبجکت CategoryResponse به صورت ایمن"""
        try:
            print(f"🔍 بررسی ساختار دسته‌بندی: {type(category)}")

            # ابتدا آبجکت را به صورت ایمن به دیکشنری تبدیل کن
            safe_category = self.safe_serialize(category)

            # اگر safe_category یک دیکشنری است، از آن استفاده کن
            if isinstance(safe_category, dict):
                category_info = {
                    "id": safe_category.get('id') or safe_category.get('_id') or id(category),
                    "name": safe_category.get('title') or safe_category.get('name') or "Unknown",
                    "name_fa": safe_category.get('title_fa') or safe_category.get('name_fa') or safe_category.get('title') or safe_category.get('name') or "نامشخص",
                    "type": "from_safe_dict",
                    "exported_at": datetime.now().isoformat()
                }
            else:
                # اگر تبدیل به دیکشنری نشد، از روش‌های قبلی استفاده کن
                category_info = {
                    "id": id(category),
                    "name": str(category),
                    "name_fa": str(category),
                    "type": "fallback_string",
                    "exported_at": datetime.now().isoformat()
                }

            # اطمینان از اینکه همه مقادیر قابل سریال‌سازی هستند
            category_info = self.safe_serialize(category_info)

            print(f"✅ دسته‌بندی استخراج شده: {category_info.get('name', 'Unknown')}")
            return category_info

        except Exception as e:
            print(f"⚠️ خطا در استخراج اطلاعات دسته‌بندی: {e}")
            return {
                "id": f"error_{id(category)}",
                "name": "Error in extraction",
                "name_fa": "خطا در استخراج",
                "type": "error",
                "error": str(e),
                "exported_at": datetime.now().isoformat()
            }

    async def get_categories_data(self) -> Optional[List[Dict[str, Any]]]:
        """دریافت داده‌های دسته‌بندی از API"""
        try:
            print("🔄 در حال دریافت اطلاعات دسته‌بندی‌ها از Basalam API...")

            # دریافت پاسخ از API
            response = await self.client.core.get_categories()

            print(f"🔍 نوع پاسخ دریافتی: {type(response)}")

            categories_list = []

            # روش ۱: اگر پاسخ یک لیست یا tuple باشد
            if isinstance(response, (list, tuple)):
                print(f"📦 پاسخ یک لیست/تاپل با {len(response)} آیتم است")
                for i, category in enumerate(response, 1):
                    print(f"🔧 پردازش دسته‌بندی {i}/{len(response)}...")
                    category_data = self.extract_category_info(category)
                    categories_list.append(category_data)

            # روش ۲: اگر پاسخ یک آبجکت تکراری باشد
            elif hasattr(response, '__iter__') and not isinstance(response, (str, dict)):
                print("📦 پاسخ قابل تکرار است")
                try:
                    raw_list = list(response)
                    print(f"📊 تعداد آیتم‌ها: {len(raw_list)}")
                    for i, category in enumerate(raw_list, 1):
                        category_data = self.extract_category_info(category)
                        categories_list.append(category_data)
                except Exception as e:
                    print(f"⚠️ خطا در تبدیل به لیست: {e}")
                    # سعی کن مستقیماً از iterator استفاده کنی
                    for i, category in enumerate(response, 1):
                        category_data = self.extract_category_info(category)
                        categories_list.append(category_data)

            # روش ۳: اگر پاسخ یک دیکشنری باشد
            elif isinstance(response, dict):
                print("📦 پاسخ یک دیکشنری است")
                for key, value in response.items():
                    category_data = self.extract_category_info(value)
                    category_data["source_key"] = key
                    categories_list.append(category_data)

            # روش ۴: اگر پاسخ یک آبجکت واحد باشد
            else:
                print("📦 پاسخ یک آبجکت واحد است")
                category_data = self.extract_category_info(response)
                categories_list.append(category_data)

            print(f"✅ تعداد دسته‌بندی‌های پردازش شده: {len(categories_list)}")
            return categories_list

        except Exception as e:
            print(f"❌ خطا در دریافت اطلاعات از API: {e}")
            import traceback
            print(f"🔍 جزئیات خطا: {traceback.format_exc()}")
            return None

    def create_structured_data(self, categories: List[Dict]) -> Dict[str, Any]:
        """ایجاد ساختار داده‌ای حرفه‌ای برای JSON"""
        # فیلتر کردن دسته‌بندی‌های معتبر
        valid_categories = []
        for cat in categories:
            if (cat.get('id') and
                not str(cat.get('id', '')).startswith('error_') and
                cat.get('name') != "Error in extraction"):
                valid_categories.append(cat)

        # ایجاد ساختار اصلی
        structured_data = {
            "metadata": {
                "project": "Basalam Categories Export",
                "version": "2.0.0",
                "export_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "export_timestamp": datetime.now().timestamp(),
                "total_categories": len(valid_categories),
                "total_raw_items": len(categories),
                "source": "Basalam API",
                "format": "JSON",
                "encoding": "UTF-8"
            },
            "export_info": {
                "generated_by": "Professional Category Exporter",
                "script_version": "2.0.0",
                "successful_categories": len(valid_categories),
                "failed_categories": len(categories) - len(valid_categories)
            },
            "categories": valid_categories
        }

        # اطمینان از قابل سریال‌سازی بودن کل ساختار
        return self.safe_serialize(structured_data)

    def save_to_json(self, data: Dict[str, Any], filename: Optional[str] = None) -> str:
        """ذخیره داده‌ها در فایل JSON با فرمت‌بندی زیبا"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"basalam_categories_{timestamp}.json"

        if not filename.endswith('.json'):
            filename += '.json'

        try:
            # استفاده از JSONEncoder سفارشی برای مدیریت آبجکت‌های غیرقابل سریال‌سازی
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4, sort_keys=False, cls=JSONSerializer)

            print(f"💾 فایل با موفقیت ذخیره شد: {filename}")
            return filename

        except Exception as e:
            print(f"❌ خطا در ذخیره‌سازی فایل: {e}")
            # روش جایگزین: ذخیره به صورت رشته
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(str(data))
                print(f"💾 فایل به صورت متن ذخیره شد: {filename}")
                return filename
            except:
                raise

    def display_summary(self, data: Dict[str, Any], filename: str):
        """نمایش خلاصه‌ای از عملیات"""
        metadata = data["metadata"]
        export_info = data["export_info"]

        print("\n" + "="*60)
        print("🎯 خلاصه عملیات استخراج دسته‌بندی‌ها")
        print("="*60)
        print(f"✅ دسته‌بندی‌های موفق: {export_info['successful_categories']}")
        print(f"⚠️  دسته‌بندی‌های ناموفق: {export_info['failed_categories']}")
        print(f"📁 نام فایل خروجی: {filename}")
        print(f"📅 تاریخ استخراج: {metadata['export_date']}")
        print(f"📊 کل آیتم‌های دریافتی: {metadata['total_raw_items']}")
        if Path(filename).exists():
            file_size = Path(filename).stat().st_size / 1024
            print(f"💾 حجم فایل: {file_size:.2f} KB")
        print("="*60)

    def display_sample_categories(self, categories: List[Dict[str, Any]]):
        """نمایش نمونه‌ای از دسته‌بندی‌های استخراج شده"""
        if not categories:
            print("📭 هیچ دسته‌بندی برای نمایش وجود ندارد.")
            return

        print("\n📋 نمونه‌ای از دسته‌بندی‌های استخراج شده:")
        print("-" * 50)

        for i, cat in enumerate(categories[:5]):
            cat_id = cat.get('id', 'N/A')
            cat_name = cat.get('name_fa', cat.get('name', 'N/A'))
            print(f"  {i+1}. 🆔 {cat_id} | 📛 {cat_name}")

        if len(categories) > 5:
            print(f"  ... و {len(categories) - 5} مورد دیگر")

        print("-" * 50)

    async def export_categories(self) -> bool:
        """تابع اصلی برای استخراج و ذخیره‌سازی دسته‌بندی‌ها"""
        try:
            # دریافت داده‌ها از API
            categories_data = await self.get_categories_data()

            if not categories_data:
                print("❌ هیچ داده‌ای برای ذخیره‌سازی دریافت نشد.")
                return False

            print(f"📦 داده‌های دریافتی: {len(categories_data)} آیتم")

            # ایجاد ساختار داده‌ای
            structured_data = self.create_structured_data(categories_data)

            # ذخیره در فایل JSON
            filename = self.save_to_json(structured_data)

            # نمایش خلاصه
            self.display_summary(structured_data, filename)

            # نمایش نمونه‌ای از داده‌ها
            valid_categories = structured_data["categories"]
            self.display_sample_categories(valid_categories)

            return True

        except Exception as e:
            print(f"❌ خطا در فرآیند استخراج: {e}")
            import traceback
            print(f"🔍 جزئیات خطا: {traceback.format_exc()}")
            return False


async def main():
    """تابع اصلی اجرای برنامه"""

    # 🔐 جایگزینی توکن‌های خود را در این قسمت انجام دهید
    TOKEN = ""
    REFRESH_TOKEN = ""

    # بررسی وجود توکن
    if not TOKEN or TOKEN == "YOUR_TOKEN_HERE":
        print("❌ لطفاً توکن خود را در متغیر TOKEN قرار دهید.")
        print("💡 توکن خود را از پنل Basalam دریافت کنید.")
        return

    try:
        # ایجاد نمونه از کلاس exporter
        exporter = CategoryExporter(TOKEN, REFRESH_TOKEN)

        print("🚀 شروع فرآیند استخراج دسته‌بندی‌ها...")
        print("⏳ لطفاً منتظر بمانید...")

        # اجرای عملیات استخراج
        success = await exporter.export_categories()

        if success:
            print("\n🎉 عملیات با موفقیت به پایان رسید!")
            print("📁 فایل JSON در پوشه جاری ایجاد شده است.")
        else:
            print("\n💥 عملیات ناموفق بود!")
            print("📞 لطفاً تنظیمات توکن و اتصال اینترنت را بررسی کنید.")

    except Exception as e:
        print(f"❌ خطای غیرمنتظره: {e}")


if __name__ == "__main__":
    # اجرای برنامه
    print("=" * 50)
    print("🛍️  Basalam Categories Exporter v2.0.0")
    print("=" * 50)

    asyncio.run(main())