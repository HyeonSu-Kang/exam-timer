import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# --- 페이지 설정 ---
st.set_page_config(page_title="만능 시험 타이머", page_icon="⏰", layout="centered")

# --- 색상 데이터 ---
COLOR_MAP = {
    "빨강": "#E74C3C", "파랑": "#3498DB", "초록": "#2ECC71",
    "노랑": "#F1C40F", "보라": "#9B59B6", "주황": "#E67E22",
    "청록": "#1ABC9C", "핑크": "#FF69B4", "회색": "#95A5A6"
}

# --- 초기 상태값(Session State) 설정 ---
if 'running' not in st.session_state:
    st.session_state.running = False
if 'paused' not in st.session_state:
    st.session_state.paused = False
if 'exam_data' not in st.session_state:
    # 기본 과목 설정
    st.session_state.exam_data = pd.DataFrame([
        {"과목명": "1교시", "시간(분)": 60, "색상": "빨강"},
        {"과목명": "2교시", "시간(분)": 60, "색상": "파랑"},
    ])
if 'real_start_dt' not in st.session_state:
    st.session_state.real_start_dt = None
if 'virtual_start_dt' not in st.session_state:
    st.session_state.virtual_start_dt = None
if 'total_paused_duration' not in st.session_state:
    st.session_state.total_paused_duration = timedelta(0)
if 'pause_start_dt' not in st.session_state:
    st.session_state.pause_start_dt = None

# =========================================================
# 1. 설정 화면 (Setup)
# =========================================================
if not st.session_state.running:
    st.title("📝 시험 스케줄 설정")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("가상 시작 시간")
        virtual_time_input = st.time_input("시험 시작 시간", value=datetime.strptime("10:00", "%H:%M").time())

    st.subheader("과목 리스트")
    # 데이터 에디터 (엑셀처럼 수정 가능)
    edited_df = st.data_editor(
        st.session_state.exam_data,
        num_rows="dynamic",
        column_config={
            "과목명": st.column_config.TextColumn("과목명"),
            "시간(분)": st.column_config.NumberColumn("시간(분)", min_value=1, max_value=300),
            "색상": st.column_config.SelectboxColumn(
                "색상",
                options=list(COLOR_MAP.keys()),
                required=True,
            )
        },
        use_container_width=True
    )

    if st.button("🚀 설정 완료 및 시작", type="primary", use_container_width=True):
        # 시작 로직
        now = datetime.now()
        st.session_state.virtual_start_dt = now.replace(
            hour=virtual_time_input.hour, 
            minute=virtual_time_input.minute, 
            second=0
        )
        st.session_state.real_start_dt = now
        st.session_state.exam_data = edited_df # 수정된 데이터 저장
        st.session_state.running = True
        st.rerun()

# =========================================================
# 2. 타이머 화면 (Timer)
# =========================================================
else:
    # --- 컨트롤 버튼 영역 ---
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🏠 처음으로 (Reset)", use_container_width=True):
            st.session_state.running = False
            st.session_state.paused = False
            st.rerun()
    with c2:
        if not st.session_state.paused:
            if st.button("⏸ 일시정지", type="primary", use_container_width=True):
                st.session_state.paused = True
                st.session_state.pause_start_dt = datetime.now()
                st.rerun()
        else:
            if st.button("▶ 재개", type="primary", use_container_width=True):
                pause_duration = datetime.now() - st.session_state.pause_start_dt
                st.session_state.total_paused_duration += pause_duration
                st.session_state.paused = False
                st.session_state.pause_start_dt = None
                st.rerun()

    # --- 화면 표시 영역 (Placeholder) ---
    # Streamlit은 루프를 돌면서 이 빈 공간을 계속 갈아끼웁니다.
    timer_placeholder = st.empty()
    clock_placeholder = st.empty()

    # --- 타이머 루프 ---
    while st.session_state.running:
        if st.session_state.paused:
            # 일시정지 상태면 화면 갱신 멈춤 (마지막 상태 유지)
            # 여기서는 간단히 "일시정지 중" 메시지만 띄움
            with timer_placeholder.container():
                st.warning("⏸ 시험이 일시정지 되었습니다.")
            time.sleep(0.5)
            # 루프를 멈추진 않지만 계산은 하지 않음
            continue

        # 1. 시간 계산
        now = datetime.now()
        elapsed = now - st.session_state.real_start_dt - st.session_state.total_paused_duration
        current_virtual_time = st.session_state.virtual_start_dt + elapsed
        total_seconds = elapsed.total_seconds()

        # 2. 현재 과목 찾기
        accumulated_min = 0
        current_section = None
        current_idx = 0
        
        exam_list = st.session_state.exam_data.to_dict('records')
        
        for idx, section in enumerate(exam_list):
            duration_min = section['시간(분)']
            if total_seconds < (accumulated_min + duration_min) * 60:
                current_section = section
                break
            accumulated_min += duration_min

        # 3. 화면 그리기
        with timer_placeholder.container():
            if current_section:
                # 남은 시간 계산
                section_elapsed_sec = total_seconds - (accumulated_min * 60)
                section_total_sec = current_section['시간(분)'] * 60
                remain_sec = section_total_sec - section_elapsed_sec
                
                rm, rs = divmod(int(remain_sec), 60)
                
                # 도넛 차트 (Plotly)
                color_hex = COLOR_MAP[current_section['색상']]
                
                fig = go.Figure(data=[go.Pie(
                    labels=['남은 시간', '경과 시간'],
                    values=[remain_sec, section_elapsed_sec],
                    hole=.7,
                    sort=False,
                    marker=dict(colors=[color_hex, '#333333']),
                    textinfo='none',
                    hoverinfo='none',
                    direction='clockwise'
                )])
                
                fig.update_layout(
                    showlegend=False,
                    margin=dict(t=0, b=0, l=0, r=0),
                    height=350,
                    annotations=[
                        dict(text=f"{rm:02}:{rs:02}", x=0.5, y=0.5, font_size=60, showarrow=False, font_color="white"),
                        dict(text=current_section['과목명'], x=0.5, y=0.35, font_size=20, showarrow=False, font_color="#AAAAAA")
                    ],
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                
                st.plotly_chart(fig, use_container_width=True)

            else:
                # 시험 종료
                st.success("🎉 모든 시험이 종료되었습니다!")
                break
        
        # 4. 가상 시계 (하단 대형 표시)
        with clock_placeholder.container():
            st.markdown(
                f"""
                <div style="text-align: center; margin-top: 20px; padding: 20px; background-color: #262730; border-radius: 10px;">
                    <p style="color: #AAAAAA; margin-bottom: 0px;">VIRTUAL CLOCK</p>
                    <p style="color: #F1C40F; font-size: 60px; font-weight: bold; margin: 0px;">
                        {current_virtual_time.strftime('%H:%M:%S')}
                    </p>
                </div>
                """, 
                unsafe_allow_html=True
            )

        time.sleep(1) # 1초 대기