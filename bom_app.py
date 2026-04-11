import streamlit as st
import pdfplumber
import pandas as pd
import re
import os

# 1. 페이지 설정 및 버전 정의
APP_VERSION = "V 1.2.1"
LAST_UPDATE = "2026.04.11"

st.set_page_config(page_title=f"SMC OPB BOM 시스템 {APP_VERSION}", layout="wide")

def show_updates():
    st.info(f"""
    **🚀 {APP_VERSION} 데이터 복구 완료 ({LAST_UPDATE})**
    * **NAME PLATE 정보 추가**: 인승(15인승) 및 용량(1150kg) 정보를 제작 사양에 포함 
    * **기준층 정보 정밀화**: TOTAL FLOOR 및 기준층(1층) 정보를 요약란에 배치 
    * **E280A 블록 고정 분석**: 메인 OPB 사양(S521A)을 E280A 행에서 직접 추출 
    * **누락 방지 로직**: 이전의 모든 주의사항, 사양, 자재 리스트를 통합하여 고정
    """)

if os.path.exists("logo.png"):
    st.image("logo.png", width=150)

st.title(f"SMC OPB생산 BOM통합 시스템 {APP_VERSION}")
show_updates()

uploaded_file = st.file_uploader("분석할 BOM PDF 파일을 선택하세요", type="pdf")

if uploaded_file:
    with pdfplumber.open(uploaded_file) as pdf:
        all_text = ""
        all_tables = []
        for page in pdf.pages:
            all_text += (page.extract_text() or "") + "\n"
            table = page.extract_table()
            if table:
                all_tables.extend(table)

    # 2. 기본 정보 추출
    project = re.search(r"공사명\s*[:\s]+([^\n]+)", all_text).group(1).strip() if "공사명" in all_text else "미확인"
    unit = re.search(r"호기번호\s*[:\s]+([A-Z0-9]+)", all_text).group(1).strip() if "호기번호" in all_text else "미확인"

    st.header(f"📊 {project} ({unit})")

    # 3. 데이터 가공 및 정밀 분석
    if all_tables:
        df_raw = pd.DataFrame(all_tables)
        header_idx = 0
        for i, row in df_raw.iterrows():
            if any(k in str(row.values) for k in ['BLOCK', '자재번호', '자재내역']):
                header_idx = i
                break
        
        df_raw.columns = df_raw.iloc[header_idx]
        df = df_raw.iloc[header_idx+1:].reset_index(drop=True).dropna(axis=1, how='all')
        df.columns = [str(c).replace('\n', ' ') for c in df.columns]

        # ---------------------------------------------------------
        # 4. [복구] 사양 추출 (E280A 및 NAME PLATE)
        # ---------------------------------------------------------
        # (1) OPB 타입 (E280A 블록 분석)
        opb_spec = "정보 없음"
        target_row = df[df.astype(str).apply(lambda x: x.str.contains('E280A')).any(axis=1)]
        if not target_row.empty:
            row_content = " ".join(target_row.values.flatten().astype(str))
            spec_find = re.search(r"OPB\s*([SD]\s*\d\s*\d\s*\d\s*[A-Z]?)", row_content, re.IGNORECASE)
            if spec_find:
                opb_spec = re.sub(r'\s+', '', spec_find.group(1))
        
        # (2) 인승 및 용량 (NAME PLATE)
        person_match = re.search(r"인승\s*(\d+)\s*인승", all_text)
        capacity_match = re.search(r"용량\s*[:\s]*(\d+)\s*kg", all_text)
        name_plate_info = f"{person_match.group(1)}인승 / {capacity_match.group(1)}kg" if person_match and capacity_match else "정보 없음"

        # (3) 층수 및 기준층
        parking_match = re.search(r"기준층\s*버튼\s*PARKING\s*SW\s*적용\s*\(([^)]+)\)", all_text)
        parking_val = parking_match.group(1) if parking_match else "미적용"
        floor_info = re.search(r"TOTAL\s*FLOOR\s*[:\s]*([0-9A-Z,\s]+)", all_text, re.IGNORECASE)
        total_floors = floor_info.group(1).split('기준층')[0].strip() if floor_info else "미확인"
        base_floor_match = re.search(r"기준층\s*[:\s]*([0-9A-Z]+)", all_text)
        base_floor = base_floor_match.group(1).strip() if base_floor_match else "미확인"

        # 5. 화면 출력
        st.subheader("⚠️ 생산 핵심 주의사항")
        c_w1, c_w2 = st.columns(2)
        with c_w1:
            if parking_val != "미적용": st.error(f"🅿️ **기준층 PARKING SW 적용: {parking_val}**")
            if "3t 적용" in all_text.lower(): st.error("🚨 **비표준 사양: OPB 표판 두께 3t 적용**")
        with c_w2:
            if "면취" in all_text: st.error("🔧 **DIS OPB 하부 면취가공 필수 (C0.5)**")
            if "비상통화장치" in all_text: st.error("🚨 **비상통화장치 적용 현장**")

        st.divider()

        st.subheader("📋 핵심 제작 사양 요약")
        c_m1, c_m2, c_m3, c_m4 = st.columns(4)
        with c_m1: st.metric("🏢 전체 층수", total_floors)
        with c_m2: st.metric("📍 기준층", base_floor)
        with c_m3: st.metric("✨ OPB 타입", opb_spec)
        with c_m4: st.metric("👥 인승/용량", name_plate_info)

        st.divider()

        st.subheader("🎛️ OPB 상세 제작 사양")
        box_match = re.search(r"BOX\s*[:\s]*([\d\s*xX,]{5,20})", all_text, re.IGNORECASE)
        sw_dwg = re.search(r"S/W\s*PANEL.*?DWG\s*NO\.?\s*[:\s]*([0-9A-Z]+)", all_text, re.IGNORECASE | re.DOTALL)
        
        r1_c1, r1_c2, r1_c3 = st.columns(3)
        with r1_c1: st.info(f"📏 **MAIN BOX size**\n\n{box_match.group(1).strip() if box_match else '정보 없음'}")
        with r1_c2: st.info(f"📄 **S/W PANEL 도면**\n\n{sw_dwg.group(1) if sw_dwg else '정보 없음'}")
        with r1_c3: 
            aircon = "✅ 적용" if any(k in all_text for k in ["AIR-CON", "에어컨"]) else "❌ 미적용"
            st.success(f"❄️ **에어컨 S/W:** {aircon}")

        st.divider()

        st.subheader("🔘 주요 자재 투입 명세 (핵심)")
        target_mask = df.astype(str).apply(lambda x: x.str.contains('BUTTON|버튼|HIP|SJ21|PCB|BOARD|E280|E281|E282', case=False, na=False)).any(axis=1)
        st.table(df[target_mask])

        st.subheader("📦 전체 자재 리스트")
        st.dataframe(df, use_container_width=True, hide_index=True)
