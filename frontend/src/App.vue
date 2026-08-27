<script setup lang="ts">
import { ref, onMounted, provide, computed } from 'vue'
import axios from 'axios'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  MarkLineComponent,
} from 'echarts/components'
import VChart, { THEME_KEY } from 'vue-echarts'
import { useThemeStore } from './stores/theme.js'

use([CanvasRenderer, LineChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent, MarkLineComponent])

const themeStore = useThemeStore()
provide(THEME_KEY, computed(() => themeStore.isDark ? 'dark' : 'light'))

const sensor = ref({ time: '', vibration: 0, temperature: 0, probability: 0 })
const history = ref([])
const alerts = ref([])

// 알람 관련 상태 및 오디오 객체
const isAlertActive = ref(false) // 중복 알람 방지용
const alertAudio = new Audio('/alert.mp3')

const maxVib = ref(0)
const maxTemp = ref(0)

// 챗봇 관련 상태
const chatMessages = ref([]) // 채팅 메시지 배열
const chatInput = ref('') // 입력 필드
const isChatOpen = ref(false) // 챗봇 창 열림/닫힘 상태
const isLoading = ref(false) // 로딩 상태

const loadInitialData = async () => {
  try {
    const res = await axios.get('http://localhost:8001/api/logs')
    const allLogs = res.data.logs

    if (allLogs && allLogs.length > 0) {
      // 1. 그래프용 히스토리 복원 (최근 50개)
      history.value = allLogs.slice(-50)

      // 2. 차트 옵션 즉시 반영
      // chartOption.value.xAxis.data = history.value.map((d) => d.time)
      // chartOption.value.series[0].data = history.value.map((d) => d.vibration)
      // chartOption.value.series[1].data = history.value.map((d) => d.temperature)

      // 3. 오늘 발생한 알람 리스트 복원 (확률 60% 초과 데이터)
      const pastAlerts = allLogs
        .filter(log => log.probability > 60)
        .reverse() // 최신순 정렬
        .map(log => ({
          id: Date.now() + Math.random(),
          time: log.time,
          prob: log.probability,
          vib: log.vibration.toFixed(2),
          temp: log.temperature.toFixed(2),
        }))

      alerts.value = pastAlerts.slice(0, 5) // 최근 5개만 화면 표시

      // 4. 오늘의 최고치 데이터 복원
      maxVib.value = Math.max(...allLogs.map(l => l.vibration), 0)
      maxTemp.value = Math.max(...allLogs.map(l => l.temperature), 0)

      console.log("과거 데이터 복원 완료:", allLogs.length, "건")
    }
  } catch (error) {
    console.error('초기 데이터 로드 실패', error)
  }
}

// PDF 다운로드 함수
const downloadPDF = async () => {
  try {
    const response = await axios.get('http://localhost:8001/api/download-report', {
      responseType: 'blob'
    })

    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `report_${new Date().toISOString().split('T')[0]}.pdf`)
    document.body.appendChild(link)
    link.click()
    link.parentNode.removeChild(link)
    window.URL.revokeObjectURL(url)

    alert('보고서가 다운로드되었습니다!')
  } catch (error) {
    console.error('PDF 다운로드 실패', error)
    alert(' PDF 다운로드에 실패했습니다.')
  }
}

// 챗봇 메시지 전송 함수
const sendChatMessage = async () => {
  if (!chatInput.value.trim()) return

  // 사용자 메시지 추가
  const userMessage = {
    type: 'user',
    text: chatInput.value,
    timestamp: new Date().toLocaleTimeString('ko-KR')
  }
  chatMessages.value.push(userMessage)

  const question = chatInput.value
  chatInput.value = ''
  isLoading.value = true

  try {
    const response = await axios.post('http://localhost:8001/api/diagnose', {
      question: question
    })

    // 봇 응답 추가
    const botMessage = {
      type: 'bot',
      text: response.data.answer,
      timestamp: new Date().toLocaleTimeString('ko-KR')
    }
    chatMessages.value.push(botMessage)

    // 자동 스크롤 (메시지가 아래로 표시되도록)
    setTimeout(() => {
      const chatBody = document.querySelector('.chat-messages')
      if (chatBody) {
        chatBody.scrollTop = chatBody.scrollHeight
      }
    }, 100)
  } catch (error) {
    console.error('진단 요청 실패', error)
    const errorMessage = {
      type: 'bot',
      text: '진단 요청에 실패했습니다. 다시 시도해주세요.',
      timestamp: new Date().toLocaleTimeString('ko-KR')
    }
    chatMessages.value.push(errorMessage)
  } finally {
    isLoading.value = false
  }
}

// 엔터 키로 메시지 전송
const handleChatKeydown = (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendChatMessage()
  }
}

const avgVib = computed(() => {
  if (history.value.length === 0) return 0
  const sum = history.value.reduce((acc, cur) => acc + cur.vibration, 0)
  return (sum / history.value.length).toFixed(2)
})

const avgTemp = computed(() => {
  if (history.value.length === 0) return 0
  const sum = history.value.reduce((acc, cur) => acc + cur.temperature, 0)
  return (sum / history.value.length).toFixed(2)
})

const getStatusClass = (val, warn, crit) => {
  if (val >= crit) return 'danger-bg'
  if (val >= warn) return 'warning-bg'
  return 'normal-bg'
}

const getStatusText = (val, warn, crit) => {
  if (val >= crit) return '🔴 위험'
  if (val >= warn) return '🟡 주의'
  return '🟢 정상'
}

const chartOption = computed(() => ({
  backgroundColor: 'transparent',
  title: {
    text: '📈 실시간 공정 데이터 추이',
    left: 'center',
    textStyle: { color: themeStore.isDark ? '#aaa' : '#333', fontSize: 14 },
  },
  tooltip: {
    trigger: 'axis',
    backgroundColor: themeStore.isDark ? 'rgba(26, 26, 26, 0.9)' : 'rgba(255, 255, 255, 0.9)',
    textStyle: { color: themeStore.isDark ? '#fff' : '#333' },
    borderColor: themeStore.isDark ? '#444' : '#ddd'
  },
  legend: {
    data: ['진동(Hz)', '온도(°C)'],
    bottom: 0,
    textStyle: { color: themeStore.isDark ? '#ccc' : '#333' }
  },
  xAxis: {
    type: 'category',
    data: history.value.map((d) => d.time),
    axisLine: { lineStyle: { color: themeStore.isDark ? '#444' : '#ddd' } }
  },
  yAxis: {
    type: 'value',
    scale: true,
    splitLine: { lineStyle: { color: themeStore.isDark ? '#222' : '#eee' } }
  },
  series: [
    {
      name: '진동(Hz)', type: 'line', data: history.value.map((d) => d.vibration), smooth: true, color: '#4facfe',
      markLine: {
        symbol: ['none', 'none'],
        data: [
          { yAxis: 15, label: { formatter: '주의(15Hz)', position: 'end' }, lineStyle: { color: '#f1c40f', type: 'dashed', opacity: 1.0 } },
          { yAxis: 25, label: { formatter: '위험(25Hz)', position: 'end' }, lineStyle: { color: '#e74c3c', type: 'solid', width: 2 } }
        ]
      }
    },
    {
      name: '온도(°C)', type: 'line', data: history.value.map((d) => d.temperature), smooth: true, color: '#91cc75',
      markLine: {
        symbol: ['none', 'none'],
        data: [
          { yAxis: 50, label: { formatter: '주의(50°C)', position: 'end' }, lineStyle: { color: '#f1c40f', type: 'dashed', opacity: 1.0 } },
          { yAxis: 65, label: { formatter: '위험(65°C)', position: 'end' }, lineStyle: { color: '#dc2626', type: 'solid', width: 2 } }
        ]
      }
    },
  ],
}))

const fetchData = async () => {
  try {
    const res = await axios.get('http://localhost:8001/api/sensor')
    const data = res.data
    sensor.value = data
    history.value.push(data)
    if (history.value.length > 50) history.value.shift()
    if (data.vibration > maxVib.value) maxVib.value = data.vibration
    if (data.temperature > maxTemp.value) maxTemp.value = data.temperature
    // chartOption.value.xAxis.data = history.value.map((d) => d.time)
    // chartOption.value.series[0].data = history.value.map((d) => d.vibration)
    // chartOption.value.series[1].data = history.value.map((d) => d.temperature)

    // 고장 알림 로직 (소리 + 팝업 통합)
    if (data.probability > 60) {
      const newAlert = {
        id: Date.now(),
        time: data.time,
        prob: data.probability,
        vib: data.vibration.toFixed(2),
        temp: data.temperature.toFixed(2),
      }
      alerts.value.unshift(newAlert)
      if (alerts.value.length > 5) alerts.value.pop()

      // 중복 알림을 방지하기 위해 isAlertActive가 false일 때만 실행
      if (!isAlertActive.value) {
        // 1) 소리 재생
        alertAudio.play().catch((e) => console.log('상호작용 후 소리 재생 가능:', e))

        // 2) 브라우저 팝업 알림
        if (Notification.permission === 'granted') {
          new Notification('설비 위험 감지!', {
            body: `현재 고장 확률 ${data.probability}%! 즉시 확인이 필요합니다.`,
            icon: '/favicon.ico', // 파비콘이 있다면 표시
          })
        }

        // 5초 동안은 추가 알람이 울리지 않도록 제어
        isAlertActive.value = true
        setTimeout(() => {
          isAlertActive.value = false
        }, 5000)
      }
    }
  } catch (error) {
    console.error('연결 실패', error)
  }
}

onMounted(() => {
  // 페이지 로드 시 브라우저 알림 권한 요청
  if (Notification.permission !== 'granted' && Notification.permission !== 'denied') {
    Notification.requestPermission()
  }

  loadInitialData()

  setInterval(fetchData, 1000)
})

</script>

<template>
  <div class="dashboard-container" :class="{ dark: themeStore.isDark }">
    <header class="main-header">
      <h1> Smart Factory Monitoring </h1>
      <div class="header-right">
        <button class="theme-toggle-btn" @click="themeStore.toggleTheme">
          {{ themeStore.isDark ? '☀️ 라이트 모드' : '🌙 다크 모드' }}
        </button>
        <button class="download-btn" @click="downloadPDF">일일 보고서 다운로드</button>
        <div class="user-info">이선우</div>
      </div>
    </header>

    <main class="dashboard-grid">
      <section class="stats-summary">
        <div class="mini-card vib-border">
          <span class="mini-label">오늘의 최고 진동</span>
          <span class="mini-value">{{ maxVib.toFixed(2) }} Hz</span>
        </div>
        <div class="mini-card vib-border">
          <span class="mini-label">평균 진동 (최근)</span>
          <span class="mini-value">{{ avgVib }} Hz</span>
        </div>
        <div class="mini-card temp-border">
          <span class="mini-label">오늘의 최고 온도</span>
          <span class="mini-value danger-text">{{ maxTemp.toFixed(2) }} °C</span>
        </div>
        <div class="mini-card temp-border">
          <span class="mini-label">평균 온도 (최근)</span>
          <span class="mini-value">{{ avgTemp }} °C</span>
        </div>
      </section>

      <section class="metrics-row">
        <div class="card" :class="getStatusClass(sensor.vibration, 15, 20)">
          <div class="label">현재 진동</div>
          <div class="value">{{ sensor.vibration.toFixed(2) }} <small>Hz</small></div>
          <div class="status-badge">{{ getStatusText(sensor.vibration, 15, 20) }}</div>
        </div>
        <div class="card" :class="getStatusClass(sensor.temperature, 55, 70)">
          <div class="label">현재 온도</div>
          <div class="value">{{ sensor.temperature.toFixed(2) }} <small>°C</small></div>
          <div class="status-badge">{{ getStatusText(sensor.temperature, 55, 70) }}</div>
        </div>
        <div class="card" :class="{ 'danger-bg': sensor.probability > 60 }">
          <div class="label">AI 고장 예측 확률</div>
          <div class="value">{{ sensor.probability }} <small>%</small></div>
          <div class="status-badge">{{ sensor.probability > 60 ? '🚨 점검 필요' : '✅ 정상' }}</div>
        </div>
      </section>

      <div class="chart-log-container">
        <section class="chart-section">
          <v-chart class="chart-box" :option="chartOption" autoresize />
        </section>

        <section class="alert-log-section">
          <h3>🚨 최근 이상 징후 이력</h3>
          <div v-if="alerts.length === 0" class="no-alert">발생한 이상 징후가 없습니다.</div>
          <ul class="alert-list">
            <li v-for="alert in alerts" :key="alert.id" class="alert-item">
              <span class="alert-time">[{{ alert.time }}]</span>
              <span class="alert-msg">
                <strong>{{ alert.prob }}%</strong> 감지
              </span>
            </li>
          </ul>
        </section>
      </div>

      <!-- 챗봇 플로팅 버튼 -->
      <button class="chatbot-float-btn" @click="isChatOpen = !isChatOpen" v-if="!isChatOpen">
        🤖
      </button>

      <!-- 챗봇 창 -->
      <div class="chatbot-container" v-if="isChatOpen">
        <div class="chatbot-header">
          <h3> 자동 진단 챗봇 </h3>
          <button class="close-btn" @click="isChatOpen = false">✕</button>
        </div>
        <div class="chat-messages">
          <div
            v-for="(msg, idx) in chatMessages"
            :key="idx"
            :class="['message', msg.type === 'user' ? 'user-msg' : 'bot-msg']"
          >
            <div class="msg-content">{{ msg.text }}</div>
            <div class="msg-time">{{ msg.timestamp }}</div>
          </div>
          <div v-if="isLoading" class="message bot-msg">
            <div class="msg-content">⏳ 진단 중...</div>
          </div>
          <div v-if="chatMessages.length === 0 && !isLoading" class="initial-msg">
            안녕하세요! 설비 상태에 대해 궁금하신 점을 물어봐주세요.
            <br><br>
            <strong>질문 예시:</strong>
            <ul>
              <li>"진동은?"</li>
              <li>"현재 온도는?"</li>
              <li>"이상있어?"</li>
              <li>"상태는?"</li>
            </ul>
          </div>
        </div>
        <div class="chat-input-area">
          <textarea
            v-model="chatInput"
            @keydown="handleChatKeydown"
            :disabled="isLoading"
            placeholder="질문을 입력하세요..."
            class="chat-input"
          ></textarea>
          <button @click="sendChatMessage" :disabled="isLoading || !chatInput.trim()" class="send-btn">
            전송
          </button>
        </div>
      </div>
    </main> </div> </template>

<style>
:root {
  --bg-color: #ffffff;
  --text-color: #333333;
  --card-bg: #f9f9f9;
  --border-color: #e0e0e0;
  --header-bg: #ffffff;
  --accent-color: #4facfe;
  --success-color: #2ecc71;
  --warning-color: #f1c40f;
  --danger-color: #e74c3c;
  --muted-text: #888888;
  --chart-bg: #f9f9f9;
  --tooltip-bg: rgba(255, 255, 255, 0.9);
  --tooltip-text: #333;
  --tooltip-border: #ddd;
}

.dark {
  --bg-color: #0d0d0d;
  --text-color: #e0e0e0;
  --card-bg: #1a1a1a;
  --border-color: #333333;
  --header-bg: #0d0d0d;
  --accent-color: #4facfe;
  --success-color: #2ecc71;
  --warning-color: #f1c40f;
  --danger-color: #e74c3c;
  --muted-text: #888888;
  --chart-bg: #1a1a1a;
  --tooltip-bg: rgba(26, 26, 26, 0.9);
  --tooltip-text: #fff;
  --tooltip-border: #444;
}

body {
  margin: 0;
  background-color: var(--bg-color);
  color: var(--text-color);
  font-family: sans-serif;
  transition: background-color 0.3s ease, color 0.3s ease;
}
.dashboard-container {
  padding: 25px;
  max-width: 1400px;
  margin: 0 auto;
  transition: background-color 0.3s ease, color 0.3s ease;
}
.chart-log-container {
  display: flex;
  gap: 20px;
  margin-top: 25px;
  align-items: stretch;
}
.main-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 25px;
  align-items: center;
}
.main-header h1 {
  color: var(--accent-color);
  margin: 0;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.theme-toggle-btn {
  background-color: var(--accent-color);
  color: white;
  border: none;
  padding: 10px 15px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: bold;
  transition: all 0.3s ease;
}

.theme-toggle-btn:hover {
  background-color: #3a9eff;
  transform: translateY(-1px);
}

.download-btn {
  background-color: var(--success-color);
  color: white;
  border: none;
  padding: 12px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: bold;
  transition: all 0.3s ease;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}
.download-btn:hover {
  background-color: #27ae60;
  transform: translateY(-2px);
  box-shadow: 0 6px 10px rgba(0, 0, 0, 0.2);
}
.download-btn:active {
  transform: translateY(0);
}
.user-info {
  color: var(--muted-text);
}

/* 통계 미니 카드 스타일 */
.stats-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 15px;
  margin-bottom: 25px;
}
.mini-card {
  background: var(--card-bg);
  padding: 15px;
  border-radius: 10px;
  border-left: 4px solid var(--border-color);
  display: flex;
  flex-direction: column;
  transition: background-color 0.3s ease;
}
.vib-border {
    border-color: #4facfe;
  }
  .temp-border {
    border-color: #2ecc71;
  }
  .warning-bg {
    border-color: #f1c40f;
  }
  .danger-bg {
    border-color: #e74c3c;
    background: rgba(231, 76, 60, 0.1);
    animation: blink 1.5s infinite;
  }

.mini-label {
  font-size: 0.75rem;
  color: var(--muted-text);
  margin-bottom: 5px;
}
.mini-value {
  font-size: 1.2rem;
  font-weight: bold;
  color: var(--text-color);
}
.danger-text {
  color: var(--danger-color);
}

.metrics-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 25px;
}
.card {
  background: var(--card-bg);
  padding: 30px;
  border-radius: 15px;
  border: 1px solid var(--border-color);
  text-align: center;
  transition: background-color 0.3s ease, border-color 0.3s ease;
}
.value {
  font-size: 3rem;
  font-weight: bold;
  color: var(--text-color);
}
.normal-bg {
  border-color: #2ecc71;
}
.warning-bg {
  border-color: #f1c40f;
}
.danger-bg {
  border-color: #e74c3c;
  background: rgba(231, 76, 60, 0.1);
  animation: blink 1.5s infinite;
}

@keyframes blink {
  50% {
    opacity: 0.7;
  }
}

.chart-section {
  background: var(--chart-bg);
  padding: 20px;
  border-radius: 15px;
  border: 1px solid var(--border-color);
  margin-bottom: 25px;
  flex: 3;
  margin-bottom: 0;
  transition: background-color 0.3s ease, border-color 0.3s ease;
}
.chart-box {
  height: 400px;
  width: 100%;
}

.alert-log-section {
  background: var(--card-bg);
  padding: 20px;
  border-radius: 15px;
  border: 1px solid var(--border-color);
  flex: 1;
  max-height: 440px;
  overflow-y: auto;
  transition: background-color 0.3s ease, border-color 0.3s ease;
}
.alert-log-section h3 {
  margin-top: 0;
  color: var(--danger-color);
  font-size: 1.1rem;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 10px;
}
.no-alert {
  color: var(--muted-text);
  text-align: center;
  padding: 20px;
}
.alert-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.alert-item {
  padding: 12px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  gap: 15px;
  font-size: 0.95rem;
  color: #ff9f43;
}
.alert-time {
  color: var(--muted-text);
  font-family: monospace;
}
.alert-msg strong {
  color: #ff4d4d;
}

/* 챗봇 스타일 */
.chatbot-float-btn {
  position: fixed;
  bottom: 30px;
  right: 30px;
  width: 70px;
  height: 70px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  color: white;
  font-size: 2rem;
  cursor: pointer;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
  transition: all 0.3s ease;
  z-index: 100;
}

.chatbot-float-btn:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
}

.chatbot-float-btn:active {
  transform: scale(0.95);
}

.chatbot-container {
  position: fixed;
  bottom: 30px;
  right: 30px;
  width: 450px;
  height: 600px;
  background: var(--card-bg);
  border-radius: 15px;
  border: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  box-shadow: 0 5px 40px rgba(0, 0, 0, 0.5);
  z-index: 101;
  transition: background-color 0.3s ease, border-color 0.3s ease;
}

.chatbot-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
  border-radius: 15px 15px 0 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #555;
}

.chatbot-header h3 {
  margin: 0;
  color: white;
  font-size: 1.1rem;
}

.close-btn {
  background: none;
  border: none;
  color: white;
  font-size: 1.5rem;
  cursor: pointer;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.close-btn:hover {
  transform: scale(1.2);
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 15px;
  background: var(--bg-color);
  transition: background-color 0.3s ease;
}

.message {
  display: flex;
  flex-direction: column;
  gap: 5px;
  max-width: 85%;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.user-msg {
  align-self: flex-end;
}

.user-msg .msg-content {
  background: #667eea;
  color: white;
  padding: 12px 16px;
  border-radius: 12px;
  border-bottom-right-radius: 4px;
  word-wrap: break-word;
  white-space: pre-wrap;
}

.bot-msg {
  align-self: flex-start;
}

.bot-msg .msg-content {
  background: var(--card-bg);
  color: var(--text-color);
  padding: 12px 16px;
  border-radius: 12px;
  border-bottom-left-radius: 4px;
  word-wrap: break-word;
  white-space: pre-wrap;
  border-left: 3px solid #667eea;
  transition: background-color 0.3s ease, color 0.3s ease;
}

.msg-time {
  font-size: 0.75rem;
  color: var(--muted-text);
  padding: 0 8px;
}

.user-msg .msg-time {
  text-align: right;
}

.initial-msg {
  text-align: center;
  color: var(--muted-text);
  padding: 20px;
  font-size: 0.95rem;
  line-height: 1.6;
}

.initial-msg ul {
  text-align: left;
  display: inline-block;
  margin: 10px 0 0 0;
  padding-left: 20px;
  list-style: none;
}

.initial-msg li {
  color: #667eea;
  margin: 5px 0;
}

.chat-input-area {
  padding: 15px;
  border-top: 1px solid var(--border-color);
  display: flex;
  gap: 10px;
  background: var(--card-bg);
  border-radius: 0 0 15px 15px;
  transition: background-color 0.3s ease, border-color 0.3s ease;
}

.chat-input {
  flex: 1;
  background: var(--bg-color);
  border: 1px solid var(--border-color);
  color: var(--text-color);
  padding: 10px 12px;
  border-radius: 8px;
  font-family: inherit;
  resize: none;
  max-height: 100px;
  font-size: 0.95rem;
  transition: background-color 0.3s ease, border-color 0.3s ease, color 0.3s ease;
}

.chat-input:focus {
  outline: none;
  border-color: #667eea;
  background: var(--bg-color);
}

.chat-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.send-btn {
  background: #667eea;
  color: white;
  border: none;
  padding: 10px 15px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.95rem;
  transition: background-color 0.3s ease;
}

.send-btn:hover:not(:disabled) {
  background: #5a67d8;
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.send-btn {
  background: #667eea;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: bold;
  transition: all 0.2s ease;
}

.send-btn:hover:not(:disabled) {
  background: #764ba2;
  transform: translateY(-2px);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.send-btn:active:not(:disabled) {
  transform: translateY(0);
}
</style>
