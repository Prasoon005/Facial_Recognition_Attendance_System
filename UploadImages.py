import os
from supabase import create_client, Client
from dotenv import load_dotenv


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
BUCKET_NAME = os.getenv("BUCKET_NAME", "images")  


supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
print(f"✅ Connected to Supabase with service role")


folder_path = "Images"


for file_name in os.listdir(folder_path):
    file_path = os.path.join(folder_path, file_name)

    
    if not os.path.isfile(file_path):
        continue

   
    try:
        supabase.storage.from_(BUCKET_NAME).remove([file_name])
        print(f"🗑️ Old file removed: {file_name}")
    except Exception as e:
        print(f"⚠️ Could not remove {file_name}: {e}")

   
    try:
        with open(file_path, "rb") as f:
            res = supabase.storage.from_(BUCKET_NAME).upload(
                file_name, f, {"x-upsert": "true"}
            )

        
        if "error" not in str(res).lower():
            print(f"✅ Uploaded successfully: {file_name}")
        else:
            print(f"❌ Error uploading {file_name}: {res}")

    except Exception as e:
        print(f"❌ Exception while uploading {file_name}: {e}")
