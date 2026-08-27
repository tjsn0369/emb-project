# Smart Factory Monitoring Project

## 프로젝트 개요

이 프로젝트는 제조 공정의 설비 상태를 모니터링하고, 진동과 온도 데이터를 기반으로 이상 징후를 예측하는 데모 프로젝트입니다. 실제로는 다음 흐름을 갖고 있습니다.

- 센서 데이터를 생성하거나 시뮬레이션합니다.
- RandomForest 기반 AI 모델로 설비 이상 확률을 계산합니다.
- FastAPI 서버가 데이터를 제공하고, 진단 질문에 대해 AI 답변을 반환합니다.
- Vue 기반 대시보드에서 실시간 상태, 이상 이력, 챗봇 기능을 표시합니다.
- 별도로 Streamlit 기반 프로토타입 대시보드도 포함되어 있습니다.

핵심 기능은 다음과 같습니다.

- 공정 센서 값의 실시간 모니터링
- 진동/온도 기준의 이상 감지
- AI 고장 확률 예측
- 설비 상태에 대한 자연어 진단 챗봇
- 대시보드 기반의 상태 시각화

---

## 기술 스택

### Backend
- Python
- FastAPI
- Uvicorn
- NumPy
- scikit-learn
- OpenAI Python SDK
- python-dotenv

### Frontend
- Vue 3
- Vite
- ECharts
- Axios

### Prototype / Demo
- Streamlit
- Plotly
- Pandas

---

## 프로젝트 구조

```text
slproject/
├── README.md
├── package.json                  # 루트 패키지 설정(주로 프론트엔드/모듈 관리 관련)
├── sl_project.py                 # Streamlit 기반 설비 모니터링 데모
├── sl_factory_data.csv           # CSV 기반 데이터 저장 파일(프로토타입용)
├── backend/
│   ├── main.py                   # FastAPI API 서버
│   ├── start_server.bat          # Windows 실행 배치
│   └── logs/                     # 일별 로그 파일 저장 위치
├── frontend/
│   ├── package.json              # Vue/Vite 프로젝트 설정
│   ├── index.html
│   ├── vite.config.js
│   ├── src/
│   │   ├── App.vue               # 메인 대시보드 화면
│   │   ├── main.js
│   │   ├── router/
│   │   ├── stores/
│   │   └── views/
│   └── public/
├── logs/
│   └── log_2026-03-31.json       # 로그 샘플
└── node_modules/                 # 설치된 의존성
```

---

## 핵심 동작 원리

### 1) AI 이상 예측
`backend/main.py`와 `sl_project.py` 두 곳 모두 RandomForestClassifier를 사용합니다.

- 입력 변수: 진동, 온도
- 출력: 정상(0) / 이상(1)
- 모델은 간단한 학습 데이터를 기반으로 초기 기준을 설정합니다.

예를 들어 학습 데이터는 다음과 같이 구성됩니다.

- 진동이 낮고 온도가 낮을수록 정상
- 진동이 높거나 온도가 높을수록 이상 가능성 증가

이 값으로 현재 센서 상태를 판별하고, 고장 확률을 계산합니다.

### 2) 백엔드 API
`backend/main.py`는 다음 API를 제공합니다.

- `GET /` : 서버 상태 확인
- `GET /api/sensor` : 현재 센서 값과 이상 확률 생성
- `POST /api/diagnose` : 최근 로그 기반으로 질문을 받아 AI 진단 응답 반환

백엔드는 OpenAI API 키가 있을 경우 질문에 대한 설명형 응답을 생성하고, 없을 경우 안내 메시지를 반환합니다.

### 3) 프론트엔드 대시보드
`frontend/src/App.vue`는 다음 기능을 포함합니다.

- 실시간 공정 데이터 시각화
- 진동, 온도, 이상 확률 카드형 표시
- 이상 징후 알림
- AI 진단 챗봇 플로팅 창
- 다크모드/라이트모드 전환
- PDF 보고서 다운로드 버튼

---

## 실행 방법

### 1) Python 백엔드 실행
Windows 환경 기준으로는 `backend/start_server.bat`를 사용할 수 있습니다.

```bat
cd backend
start_server.bat
```

또는 직접 실행:

```bash
cd backend
python -m venv .venv
. .venv/bin/activate      # macOS/Linux
# 또는 .venv\Scripts\activate   # Windows
pip install fastapi uvicorn numpy scikit-learn python-dotenv openai
python main.py
```

기본 실행 주소는 다음과 같습니다.

- http://localhost:8001

필요한 경우 `.env` 파일을 추가해 주세요.

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-3.5-turbo
```

### 2) Vue 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
```

기본 개발 서버 주소는 다음과 같습니다.

- http://localhost:5173

### 3) Streamlit 데모 실행

```bash
cd slproject
streamlit run sl_project.py
```

---

## 사용 시나리오

### 시나리오 1: 실시간 설비 상태 확인
- 대시보드에서 현재 진동, 온도, 고장 확률을 확인합니다.
- 확률이 높으면 경고 상태를 표시합니다.

### 시나리오 2: 이상 원인 진단
- 챗봇에 질문을 입력합니다.
- 예시: "현재 상태는 어떤가?", "진동이 높은 이유는 무엇인가?", "이상 징후가 있나?"
- 서버는 최근 센서 값을 기준으로 답변을 생성합니다.

### 시나리오 3: 로그 기반 추적
- `backend/logs` 또는 데이터 파일에 저장된 로그를 확인하여 일별 상태 추이를 추적할 수 있습니다.

---

## 주의사항

- OpenAI 연동은 선택 사항이며, API 키가 없으면 AI 답변 생성이 비활성화됩니다.
- 현재 프로젝트는 데모/시뮬레이션 중심이며, 실제 공장 데이터 연결 전용 구조라기보다는 학습 및 프로토타입용 구성입니다.
- 프론트엔드와 백엔드가 같은 포트/도메인 구조를 맞추기 위해 CORS가 허용되어 있으며, 실제 배포 시 보안 설정을 별도로 검토해야 합니다.

---

## 향후 확장 아이템

- 실제 PLC/센서 클라이언트 연동
- MySQL 또는 PostgreSQL 저장소 연결
- 장비별 추세 분석 및 예측 모델 고도화
- 일별/월간 보고서 자동 생성
- 관리자용 로그인 및 권한 관리
- 알림 전송(메일, SMS, Slack)

---

## 요약

이 프로젝트는 설비 이상 탐지와 AI 기반 진단을 결합한 스마트 팩토리 데모로, 실시간 모니터링과 AI 응답 기능을 한 번에 보여주기 위한 구조입니다. 빠르게 시연할 수 있는 형태로 구성되어 있으며, 실제 운영 환경을 위해서는 데이터 저장, 보안, 모델 성능 개선, 운영 환경 배포 단계가 추가로 필요합니다.
