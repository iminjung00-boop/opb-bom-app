import streamlit as st
import pdfplumber
import pandas as pd
import re
import os

# 1. 페이지 설정
st.set_page_config(page_title="SMC OPB생산 BOM통합 시스템 V 1.0", layout="wide")

if os.path.exists("logo.png"):
    st.image("logo.png", width=150)

st.title("SMC OPB생산 BOM통합 시스템 V 1.0")
st.write("기준층 정보 및 전체 층수 사양을 포함하여 모든 제작 정보를 분석합니다.")

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

    # 2. 정보 추출
    project = re.search(r"공사명\s*[:\s]+([^\n]+)", all_text).group(1).strip() if "공사명" in all_text else "미확인"
    unit = re.search(r"호기번호\s*[:\s]+([A-Z0-9]+)", all_text).group(1).strip() if "호기번호" in all_text else "미확인"

    st.header(f"📊 {project} ({unit})")

    # 3. 🚨 생산 핵심 주의사항
    st.subheader("⚠️ 생산 핵심 주의사항")
    opb_3t = "3t 적용" in all_text or "3T 적용" in all_text
    emergency_light = "비상통화장치 동작 표시등 적용" in all_text
    # 기준층 파킹 스위치 정보 추출 (예: 1층 적용)
    parking_match = re.search(r"기준층\s*버튼\s*PARKING\s*SW\s*적용\s*\(([^)]+)\)", all_text)
    parking_val = parking_match.group(1) if parking_match else "미적용"
    
    col_warn1, col_warn2 = st.columns(2)
    with col_warn1:
        if opb_3t: st.error("🚨 **비표준 사양: OPB 표판 두께 3t 적용**")
        if parking_val != "미적용":
            st.warning(f"🅿️ **기준층 PARKING SW 적용: {parking_val}**")
        if emergency_light: st.error("🚨 **비상통화장치 동작 표시등 적용 현장**")
    with col_warn2:
        if "면취" in all_text: st.error("🔧 **DIS OPB 하부 면취가공 필수 (C0.5)**")
        dwgs = re.findall(r"DWG\.?\s*([0-9A-Z]{7,10})", all_text)
        if dwgs:
            for d in set(dwgs): st.error(f"🚨 **비표준 도면 확인 필수: {d}**")

    st.divider()

    # 4. 🎛️ 제작 상세 규격 요약
    st.subheader("📋 핵심 제작 사양 요약")
    # 전체 층수 정보 (B2, B1... 형태)
    floor_match = re.search(r"TOTAL\s*FLOOR\s*([^\n]+)", all_text, re.IGNORECASE)
    floor_val = floor_match.group(1).split('기준층')[0].strip() if floor_match else "미확인"
    
    c_m1, c_m2, c_m3 = st.columns(3)
    with c_m1:
        st.metric("🏢 전체 층수 (FLOORS)", floor_val)
    with c_m2:
        st.metric("📍 기준층 위치", parking_val)
    with c_m3:
        material = "MIRROR" if any(k in all_text for k in ["미러", "MIRROR"]) else "HAIRLINE"
        st.metric("✨ 표면 사양", f"ST'S {material}")

    st.divider()

    # 5. 🎛️ OPB 상세 제작 사양
    st.subheader("🎛️ OPB 및 S/W PANEL 상세 사양")
    box_match = re.search(r"BOX\s*[:\s]*([\d\s*xX,]{5,20})", all_text, re.IGNORECASE)
    sw_dwg = re.search(r"S/W\s*PANEL.*?DWG\s*NO\.?\s*[:\s]*([0-9A-Z]+)", all_text, re.IGNORECASE | re.DOTALL)
    indicator_data = re.search(r"INDICATOR\s*DATA\s*[:\s]*([^\n]+)", all_text, re.IGNORECASE)

    c1, c2, c3 = st.columns(3)
    with c1: st.info(f"📏 **MAIN BOX size**\n\n{box_match.group(1).strip() if box_match else '정보 없음'}")
    with c2: st.info(f"📄 **S/W PANEL 도면**\n\n{sw_dwg.group(1) if sw_dwg else '정보 없음'}")
    with c3: st.info(f"📟 **인디케이터 문구**\n\n{indicator_data.group(1).strip() if indicator_data else '정보 없음'}")

    st.divider()

    # 6. 자재 리스트 분석
    if all_tables:
        df_raw = pd.DataFrame(all_tables)
        header_idx = 0
        for i, row in df_raw.iterrows():
            if any(k in str(row.values) for k in ['품명', 'NAME', '사양']):
                header_idx = i; break
        
        cols = list(df_raw.iloc[header_idx]); new_cols = []
        for i, val in enumerate(cols):
            val = str(val) if val else f"Unknown_{i}"
            if val in new_cols: new_cols.append(f"{val}_{i}")
            else: new_cols.append(val)
        df_raw.columns = new_cols
        df = df_raw.iloc[header_idx+1:].reset_index(drop=True).dropna(axis=1, how='all')

        st.subheader("🔘 버튼 및 주요 자재 투입 명세")
        target_mask = df.astype(str).apply(lambda x: x.str.contains('BUTTON|버튼|HIP|SJ21|PCB|BOARD|E280A|E281A', case=False, na=False)).any(axis=1)
        st.table(df[target_mask])

        st.subheader("📦 전체 자재 리스트")
        st.dataframe(df, use_container_width=True, hide_index=True)
