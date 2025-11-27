from supabase import create_client
import os
from dotenv import load_dotenv

# env load
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# student update
response = supabase.table("students").update({"name": "Prasoon Katiyar"}).eq("id", "321654").execute()

print("Update Result:", response.data)
