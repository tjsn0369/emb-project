import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime
import os
import plotly.graph_objects as go
from sklearn.ensemble import RandomForestClassifier

#--- 실시간 데이터 저장을 위한 CSV 파일 경로 설정 ---
DB_FILE = "sl_factory_data.csv"

if not os.path.exists(DB_FILE):
    df_init = pd.DataFrame(columns=['시간', '진동', '온도', '상태'])
    df_init.to_csv(DB_FILE, index=False, encoding='utf-8-sig')

    #--- 데이터 저장 로직 ---
def save_to_csv(data):
    df_to_save = pd.DataFrame([data])
    df_to_save.to_csv(DB_FILE, mode='a', index=False, header=False, encoding='utf-8-sig')

# --- AI 모델 생성 및 가상 학습 ---
# 실제 데이터가 쌓이기 전까지 AI가 판단 기준을 가질 수 있도록 기초 학습을 시킵니다.
@st.cache_resource
def train_ai_model():
    # 학습 데이터 생성 (진동, 온도) -> (정상:0, 이상:1)
    # 진동이 높거나 온도가 높으면 '이상'으로 학습
    train_x = [[10, 45], [12, 46], [9, 44], [11, 45], [25, 60], [22, 58], [28, 65], [10, 70]]
    train_y = [0, 0, 0, 0, 1, 1, 1, 1] 
    
    model = RandomForestClassifier(n_estimators=100)
    model.fit(train_x, train_y)
    return model

ai_engine = train_ai_model()

#--- 1. 대시보드 화면 설정 ---
st.set_page_config(page_title="Smart Factory", layout="wide")
st.title("🚗 Smart Factory Dashboard 🚗")
st.sidebar.header("설비 상태 모니터링")
st.sidebar.info("이선우")

#---2. 데이터 저장 공간 만들기 ---
if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['시간', '진동', '온도', '상태'])

placeholder = st.empty() # 화면 새로고침

# --- 3. 실시간 화면 업데이트 ---
for i in range(1000):
    with placeholder.container():
        curr_time = datetime.now().strftime("%H:%M:%S")
        
        # 1. 데이터 생성 (가끔 이상 데이터 발생 시뮬레이션)
        is_error = np.random.rand() > 0.9 # 10% 확률로 고장 징후
        if is_error:
            vibration = np.random.normal(22, 3)
            temperature = np.random.normal(55, 5)
        else:
            vibration = np.random.normal(10, 2)
            temperature = np.random.normal(45, 1)

        # 2. [AI의 판단] 머신러닝 모델이 현재 데이터를 분석
        # 고장일 확률(Probability)을 계산합니다.
        prob = ai_engine.predict_proba([[vibration, temperature]])[0][1] 
        prob_percent = round(prob * 100, 1)
        
        if prob > 0.6: # 고장 확률이 60% 이상이면
            status = "🚨 이상 감지"
            st.error(f"**[AI 경고]** 설비 이상 발생 확률이 {prob_percent}%로 높습니다! 즉시 점검 필요.")
        elif prob > 0.3:
            status = "⚠️ 주의"
            st.warning(f"**[AI 분석]** 설비 상태가 불안정합니다. (고장 확률: {prob_percent}%)")
        else:
            status = "✅ 정상"

        # 3. 데이터 딕셔너리 생성 및 저장
        current_data = {
            '시간': curr_time, 
            '진동': round(vibration, 2), 
            '온도': round(temperature, 2), 
            '상태': status,
            '고장확률': f"{prob_percent}%"
        }
        save_to_csv(current_data)

        # 4. 화면 표시용 데이터 업데이트
        new_row = pd.DataFrame([current_data])
        st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True).tail(20)

        # 5. 시각화 (Metric & Graph)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("현재 진동 (Hz)", f"{current_data['진동']}")
        col2.metric("현재 온도 (°C)", f"{current_data['온도']}")
        col3.metric("고장 확률", f"{prob_percent}%")
        col4.metric("종합 상태", status)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=st.session_state.history['시간'], y=st.session_state.history['진동'], name="진동(Hz)"))
        fig.add_trace(go.Scatter(x=st.session_state.history['시간'], y=st.session_state.history['온도'], name="온도(°C)"))
        fig.update_layout(height=350, margin=dict(l=20, r=20, t=40, b=20), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True)

        # 6. 실시간 로그 데이터
        st.write("### 📊 실시간 분석 로그")
        st.table(st.session_state.history.tail(5))

        time.sleep(1)