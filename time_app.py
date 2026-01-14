import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time

# --- 페이지 설정 ---
st.set_page_config(page_title="만능 시험 타이머", page_icon="⏰", layout="centered")

# --- 스타일(CSS) 설정: 깜빡임 방지 및 디자인 ---
st.markdown("""
<style>
    /* 전체 배경 및 폰트 */
    .main { background-color: #0E1117; }
    
    /* 도넛 차트 컨테이너 */
    .donut-container {
        position: relative;
        width: 300px;
        height: 300px;
        margin: 0 auto;
    }
    
    /* 중앙 텍스트 */
    .donut-text {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        text-align: center;
    }
    .time-text { font-size: 48px; font-weight: bold; color: white; margin: 0; }
    .label-text { font-size: 18px; color: #AAAAAA; margin: 0; }

    /* 가상 시계 박스 */
    .clock-box {
        text-align: center;
        margin-top: 20px;
        padding: 15px;
        background-color: #262730;
        border-radius: 10px;
        border: 1px solid #333;
    }
    .clock-time {
        color: #F1C40F;
        font-size: 55px;
        font-weight: bold;
        margin: 0;
        font-family: 'Courier New', monospace; /* 고정폭 글꼴로 숫자 흔들림 방지 */
    }
</style>
""", unsafe_allow_html=True)

# --- 색상 데이터 ---
COLOR_MAP = {
    "빨강": "#E74C3C", "파랑": "#3498DB", "초록": "#2ECC71",
    "노랑": "#F1C40F", "보라": "#9B59B6", "주황": "#E67E22",
    "청록": "#1ABC9C", "핑크": "#FF69B4", "회색": "#95A5A6"
}

# --- HTML 도넛 차트 생성 함수 (가벼움!) ---
def make_donut_html(percent, color, time_str, label_str):
    # SVG를 사용하여 가볍게 그립니다
    return f"""
    <div class="donut-container">
        <svg width="300" height="300" viewBox="0 0 42 42">
            <circle cx="21" cy="21" r="15.91549430918954" fill="transparent" stroke="#333" stroke-width="4"></circle>
            <circle cx="21" cy="21" r="15.91549430918954" fill="transparent" stroke="{color}" stroke-width="4"
                stroke-dasharray="{percent} {100-percent}" stroke-dashoffset="25"
                style="transition: stroke-dasharray 0.5s ease;"></circle>
        </svg>
        <div class="donut-text">
            <p class="time-text">{time_str}</p>
            <p class="label-text">{label_str}</p>
        </div>
    </div>
    """

# --- 초기 상태값 설정 ---
if 'running' not in st.session_state: st.session_state.running = False
if 'paused' not in st.session_state: st.session_state.paused = False
if 'exam_data' not in st.session_state:
    st.session_state.exam_data = pd.DataFrame([
        {"과목명": "1교시", "시간(분)": 60, "색상": "빨강"},
        {"과목명": "2교시", "시간(분)": 60, "색상": "파랑"},
    ])
if 'real_start_dt' not in st.session_state: st.session_state.real_start_dt = None
if 'virtual_start_dt' not in st.session_state: st.session_state.virtual_start_dt = None
if 'total_paused_duration' not in st.session_state: st.session_state.total_paused_duration = timedelta(0)
if 'pause_start_dt' not in st.session_state: st.session_state.pause_start_dt = None

# =========================================================
# 1. 설정 화면
# =========================================================
if not st.session_state.running:
    st.title("📝 시험 스케줄 설정")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("가상 시작 시간")
        # step=60 추가로 1분 단위 조절 가능
        virtual_time_input = st.time_input("시험 시작 시간", value=datetime.strptime("10:00", "%H:%M").time(), step=300)

    st.subheader("과목 리스트")
    edited_df = st.data_editor(
        st.session_state.exam_data,
        num_rows="dynamic",
        column_config={
            "과목명": st.column_config.TextColumn("과목명"),
            "시간(분)": st.column_config.NumberColumn("시간(분)", min_value=1, max_value=300),
            "색상": st.column_config.SelectboxColumn("색상", options=list(COLOR_MAP.keys()), required=True)
        },
        use_container_width=True
    )

    if st.button("🚀 설정 완료 및 시작", type="primary", use_container_width=True):
        now = datetime.now()
        st.session_state.virtual_start_dt = now.replace(hour=virtual_time_input.hour, minute=virtual_time_input.minute, second=0)
        st.session_state.real_start_dt = now
        st.session_state.exam_data = edited_df
        st.session_state.running = True
        st.rerun()

# =========================================================
# 2. 타이머 화면
# =========================================================
else:
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🏠 처음으로 (Reset)", use_container_width=True):
            st.session_state.running = False; st.session_state.paused = False; st.rerun()
    with c2:
        if not st.session_state.paused:
            if st.button("⏸ 일시정지", type="primary", use_container_width=True):
                st.session_state.paused = True
                st.session_state.pause_start_dt = datetime.now()
                st.rerun()
        else:
            if st.button("▶ 재개", type="primary", use_container_width=True):
                st.session_state.total_paused_duration += (datetime.now() - st.session_state.pause_start_dt)
                st.session_state.paused = False
                st.session_state.pause_start_dt = None
                st.rerun()

    timer_placeholder = st.empty()
    clock_placeholder = st.empty()

    while st.session_state.running:
        if st.session_state.paused:
            with timer_placeholder.container():
                st.warning("⏸ 시험이 일시정지 되었습니다.")
            time.sleep(0.5)
            continue

        # 시간 계산
        now = datetime.now()
        elapsed = now - st.session_state.real_start_dt - st.session_state.total_paused_duration
        current_virtual_time = st.session_state.virtual_start_dt + elapsed
        total_seconds = elapsed.total_seconds()

        # 현재 과목 찾기
        accumulated_min = 0; current_section = None; 
        exam_list = st.session_state.exam_data.to_dict('records')
        
        for section in exam_list:
            if total_seconds < (accumulated_min + section['시간(분)']) * 60:
                current_section = section; break
            accumulated_min += section['시간(분)']

        # 화면 그리기 (HTML 방식)
        with timer_placeholder.container():
            if current_section:
                section_elapsed = total_seconds - (accumulated_min * 60)
                section_total = current_section['시간(분)'] * 60
                remain = section_total - section_elapsed
                
                # 퍼센트 계산 (남은 시간 비율)
                percent = (remain / section_total) * 100
                if percent < 0: percent = 0
                
                rm, rs = divmod(int(remain), 60)
                time_str = f"{rm:02}:{rs:02}"
                color_hex = COLOR_MAP[current_section['색상']]

                # ★ Plotly 대신 가벼운 HTML 코드 삽입
                st.markdown(make_donut_html(percent, color_hex, time_str, current_section['과목명']), unsafe_allow_html=True)
            else:
                st.success("🎉 모든 시험이 종료되었습니다!")
                break
        
        # 가상 시계 (하단)
        with clock_placeholder.container():
            st.markdown(f"""
                <div class="clock-box">
                    <p style="color:#AAAAAA; margin-bottom:5px;">VIRTUAL CLOCK</p>
                    <p class="clock-time">{current_virtual_time.strftime('%H:%M:%S')}</p>
                </div>
            """, unsafe_allow_html=True)

        time.sleep(1)
