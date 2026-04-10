import streamlit as st
import pdfplumber
import pandas as pd
import re
import os

# 1. 페이지 설정
st.set_page_config(page_title="엘리베이터 BOM 통합 분석기", layout="wide")

if os.path.exists("logo.png"):
    st.image("logo.png", width=150)

st.title("🏭 엘리베이터 생산 BOM 통합 분석 시스템")
st.write("비상통화장치 표시등 및 주요 제작 사양을 자동으로 구분하여 분석합니다.")

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

    # 3. 🚨 [최상단] 생산 핵심 주의사항
    st.subheader("⚠️ 생산 핵심 주의사항 (FIRST CHECK)")
    
    # 비상통화장치 동작 표시등 감지
    emergency_light = "비상통화장치 동작 표시등" in all_text or "비상통화장치" in all_text
    open_dir_match = re.search(r"열림방향(?:\(MAIN\))?\s*[:\s]*([가-힣A-Z/]+)", all_text)
    open_direction = open_dir_match.group(1) if open_dir_match else "미확인"
    dwgs = re.findall(r"DWG\.?\s*([0-9A-Z]{7,10})", all_text)
    
    col_warn1, col_warn2 = st.columns(2)
    with col_warn1:
        st.warning(f"🚪 **열림방향(MAIN): {open_direction}**")
        if emergency_light:
            st.error("🚨 **비상통화장치 동작 표시등 적용 현장 (명판 확인 필수)**")
        if "면취" in all_text:
            st.error("🔧 **DIS OPB 하부 면취가공 필수 (C0.5)**")

    with col_warn2:
        if dwgs:
            for d in set(dwgs):
                st.error(f"🚨 **비표준 도면 확인 필수: {d}**")
        else:
            st.success("✅ **표준 도면 사양 (특이사항 없음)**")

    st.divider()

    # 4. 📋 핵심 제작 정보 요약
    st.subheader("📋 핵심 제작 사양 요약")
    floor_match = re.search(r"TOTAL\s*FLOOR\s*[:\s]*([^\n]+)", all_text, re.IGNORECASE)
    total_floor_detail = floor_match.group(1).strip() if floor_match else "미확인"
    box_size = re.search(r"BOX\s*[:\s]*([\d\s*xX]+)", all_text)
    material = "MIRROR" if any(k in all_text for k in ["미러", "MIRROR"]) else "HAIRLINE"

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("🏢 전체 층수 (TOTAL)", total_floor_detail)
    with c2:
        st.metric("📏 BOX 규격", box_size.group(1) if box_size else "미확인")
    with c3:
        st.metric("✨ 표면 사양", f"ST'S {material}")

    # 5. 상세 리스트 (버튼 및 NAME PLATE)
    if all_tables:
        df_raw = pd.DataFrame(all_tables)
        header_idx = 0
        for i, row in df_raw.iterrows():
            if any(k in str(row.values) for k in ['품명', 'NAME', '사양']):
                header_idx = i; break
        df_raw.columns = df_raw.iloc[header_idx]
        df = df_raw.iloc[header_idx+1:].reset_index(drop=True).dropna(axis=1, how='all')

        # --- NAME PLATE 상세 분석 (비상통화등 사양 추가) ---
        st.markdown("---")
        st.subheader("🏷️ NAME PLATE & 제작 사양")
        
        name_plate_mask = df.astype(str).apply(lambda x: x.str.contains('NAME PLATE|명판|NAMEPLATE', case=False, na=False)).any(axis=1)
        name_plate_df = df[name_plate_mask].copy()

        if not name_plate_df.empty:
            # 비상통화장치 표시등 적용 여부를 명판 비고란에 강제 표기
            if emergency_light:
                st.info("💡 **이 현장의 NAME PLATE에는 '비상통화장치 동작 표시등' 사양이 포함되어야 합니다.**")
            st.table(name_plate_df)
        else:
            st.info("명판 상세 항목을 찾지 못했습니다.")

        st.subheader("🔘 버튼 투입 명세")
        btn_mask = df.astype(str).apply(lambda x: x.str.contains('BUTTON|버튼|HIP|SJ21', case=False, na=False)).any(axis=1)
        st.table(df[btn_mask])

        st.divider()
        st.subheader("📦 전체 자재 리스트")
        st.dataframe(df, use_container_width=True, hide_index=True)
