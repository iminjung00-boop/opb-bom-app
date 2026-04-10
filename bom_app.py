import streamlit as st
import pdfplumber
import pandas as pd
import re
import os

# 1. 페이지 설정 및 버전 정의
APP_VERSION = "V 1.1.1"
LAST_UPDATE = "2026.04.10"

st.set_page_config(page_title=f"SMC OPB BOM 시스템 {APP_VERSION}", layout="wide")

# 버전 체크 알림 기능
def version_check():
    if 'version_notified' not in st.session_state:
        st.toast(f"🚀 {APP_VERSION} 업데이트 완료", icon="✅")
        st.info(f"""
        **📢 {APP_VERSION} 업데이트 안내**
        * **자재 필터링 강화**: E280, E281, E282 등 주요 장치 코드 누락 방지 로직 적용
        * **전체 리스트 보기 추가**: 필터링된 표 외에 전체 자재 리스트를 하단에 상시 배치
        """)
        st.session_state['version_notified'] = True

if os.path.exists("logo.png"):
    st.image("logo.png", width=150)

st.title(f"SMC OPB생산 BOM통합 시스템 {APP_VERSION}")
version_check()

uploaded_file = st.file_uploader("분석할 BOM PDF 파일을 선택하세요", type="pdf")

if uploaded_file:
    with pdfplumber.open(uploaded_file) as pdf:
        all_text = ""
        all_tables = []
        for page in pdf.pages:
            all_text += (page.extract_text() or "") + "\n"
            # 표 추출 로직 강화 (여러 페이지의 표를 수집)
            table = page.extract_table()
            if table:
                all_tables.extend(table)

    # 2. 정보 추출
    project = re.search(r"공사명\s*[:\s]+([^\n]+)", all_text).group(1).strip() if "공사명" in all_text else "미확인"
    unit = re.search(r"호기번호\s*[:\s]+([A-Z0-9]+)", all_text).group(1).strip() if "호기번호" in all_text else "미확인"

    st.header(f"📊 {project} ({unit})")

    # 3. 🚨 생산 핵심 주의사항
    st.subheader("⚠️ 생산 핵심 주의사항")
    parking_match = re.search(r"기준층\s*버튼\s*PARKING\s*SW\s*적용\s*\(([^)]+)\)", all_text)
    parking_val = parking_match.group(1) if parking_match else "미적용"
    opb_3t = "3t 적용" in all_text or "3T 적용" in all_text
    
    col_warn1, col_warn2 = st.columns(2)
    with col_warn1:
        if parking_val != "미적용":
            st.error(f"🅿️ **기준층 PARKING SW 적용: {parking_val} (제작 주의)**")
        if opb_3t: st.error("🚨 **비표준 사양: OPB 표판 두께 3t 적용**")
    with col_warn2:
        if "면취" in all_text: st.error("🔧 **DIS OPB 하부 면취가공 필수 (C0.5)**")
        if "비상통화장치" in all_text: st.error("🚨 **비상통화장치 동작 표시등 적용 현장**")

    st.divider()

    # 4. 📋 핵심 제작 사양 요약
    st.subheader("📋 핵심 제작 사양 요약")
    floor_info_match = re.search(r"TOTAL\s
