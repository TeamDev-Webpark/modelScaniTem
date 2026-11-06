import os

# โฟลเดอร์เป้าหมาย
folder_path = 'mock_database'
abs_path = os.path.abspath(folder_path)

print(f"📂 กำลังตรวจสอบที่อยู่: {abs_path}")

if not os.path.exists(folder_path):
    print("❌ ไม่พบโฟลเดอร์นี้! (Folder not found)")
else:
    all_files = os.listdir(folder_path)
    print(f"📦 พบไฟล์ทั้งหมด {len(all_files)} รายการ (รวมทุกประเภท):")
    
    found_image = False
    for f in all_files:
        print(f"   - {f}")
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            found_image = True
            
    if not found_image:
        print("\n⚠️ ปัญหาเจอแล้ว: มีไฟล์ในโฟลเดอร์ แต่ไม่มีไฟล์นามสกุล .png, .jpg, .jpeg เลย")
        print("   -> ลองตรวจสอบว่าไฟล์เป็น .webp หรือนามสกุลอื่นหรือไม่?")
    else:
        print("\n✅ มีไฟล์รูปภาพปกติ แต่ทำไม scanner มองไม่เห็น?")