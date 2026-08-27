import json
import os
import numpy as np
import uvicorn
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# FastAPI 및 관련 라이브러리
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sklearn.ensemble import RandomForestClassifier

# .env 환경변수 로드
load_dotenv()

# OpenAI 클라이언트 초기화
api_key = os.environ.get("OPENAI_API_KEY")
model_name = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
client = OpenAI(api_key=api_key) if api_key else None

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "설비 관리 AI 챗봇 API가 실행 중입니다."}

# 경로 및 로그 설정
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# AI 모델 초기화
def train_ai_model():
    train_x = [[10, 45], [12, 46], [9, 44], [11, 45], [25, 60], [22, 58], [28, 65], [10, 70]]
    train_y = [0, 0, 0, 0, 1, 1, 1, 1] 
    model = RandomForestClassifier(n_estimators=100)
    model.fit(train_x, train_y)
    return model

ai_engine = train_ai_model()

# 로그 관리 함수
def get_today_log_file():
    return LOG_DIR / f"log_{date.today().strftime('%Y-%m-%d')}.json"

def save_log(data):
    log_file = get_today_log_file()
    logs = json.load(open(log_file, 'r', encoding='utf-8')) if log_file.exists() else []
    logs.append(data)
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

def get_today_logs():
    log_file = get_today_log_file()
    return json.load(open(log_file, 'r', encoding='utf-8')) if log_file.exists() else []

# AI 챗봇 응답 함수
def ask_openai(context: str, question: str) -> str:
    if not client:
        return "AI 서비스가 설정되지 않았습니다."
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "너는 설비 관리 전문가야. 한국어로 답변해."},
                {"role": "user", "content": f"현재 센서 정보: {context}\n질문: {question}"}
            ]
        )
        # 중요: 가져온 답변을 문자열로 확실히 변환하고, 인코딩 에러를 유발하는 문자는 무시합니다.
        raw_text = response.choices[0].message.content
        return raw_text.encode('utf-8', 'ignore').decode('utf-8', 'ignore').strip()
    except Exception as e:
        # 에러 메시지 자체를 출력하지 않고 고정 문구만 반환하여 인코딩 충돌 원천 차단
        return "답변 처리 중 오류가 발생했습니다."
    
# API 엔드포인트
@app.get("/api/sensor")
async def get_sensor_data():
    is_error = np.random.rand() > 0.9
    vibr = np.random.normal(25, 2) if is_error else np.random.normal(10, 1)
    temp = np.random.normal(60, 2) if is_error else np.random.normal(40, 1)
    prob = ai_engine.predict_proba([[vibr, temp]])[0][1]
    
    data = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "vibration": round(float(vibr), 2),
        "temperature": round(float(temp), 2),
        "probability": round(float(prob * 100), 2),
        "status": "✅ 정상" if prob * 100 < 60 else "🚨 이상"
    }
    save_log(data)
    return data

@app.post("/api/diagnose")
async def diagnose(request: Request):
    payload = await request.json()
    user_question = payload.get('question', '').strip()
    logs = get_today_logs()

    if not user_question:
        return {"answer": "질문을 입력해 주세요."}
    if not logs:
        return {"answer": "수집된 데이터가 없습니다."}

    latest = logs[-1]
    context = f"시간: {latest.get('time')}, 진동: {latest['vibration']}Hz, 온도: {latest['temperature']}°C, 상태: {latest['status']}"
    
    answer = ask_openai(context, user_question)
    return {"answer": answer}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)