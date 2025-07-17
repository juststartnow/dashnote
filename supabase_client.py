import os
from supabase import create_client, Client
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 환경변수 불러오기
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

# Supabase 클라이언트 생성
supabase: Client = create_client(url, key)