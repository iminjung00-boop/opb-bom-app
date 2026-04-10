import streamlit as st
import pdfplumber
import pandas as pd
import re
import os

# 1. 페이지 설정
st.set_page_config(page_title="엘리베이터 BOM 분석", layout="wide")

if os.path.exists("logo.png"):
    st.image("logo.png", width=150)

st.title("SMC OPB 생산 BOM 분석 V1.0")
st.write("생산 주의사항을 최우선으로 확인하고, 상세 층수 및 버튼 구성을 분석합니다.")

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

    # ---------------------------------------------------------
    # 3. [최상단] 🚨 생산 핵심 주의사항 (가장 먼저 확인!)
    # ---------------------------------------------------------
    st.subheader("⚠️ 생산 핵심 주의사항 (FIRST CHECK)")
    
    # 열림방향 및 도면번호 추출
    open_dir_match = re.search(r"열림방향(?:\(MAIN\))?\s*[:\s]*([가-힣A-Z/]+)", all_text)
    open_direction = open_dir_match.group(1) if open_dir_match else "미확인"
    dwgs = re.findall(r"DWG\.?\s*([0-9A-Z]{7,10})", all_text)
    
    col_warn1, col_warn2 = st.columns(2)
    with col_warn1:
        # 열림방향과 면취가공 강조
        st.warning(f"🚪 **열림방향(MAIN): {open_direction}**")
        if "면취" in all_text:
            st.error("🔧 **DIS OPB 하부 면취가공 필수 (C0.5)**")
        if "벨버튼" in all_text:
            st.warning("🔘 **벨버튼 위치: [열림/닫힘] 버튼 하단 배치**")

    with col_warn2:
        # 비표준 도면 경고
        if dwgs:
            for d in set(dwgs):
                st.error(f"🚨 **비표준 도면 확인 필수: {d}**")
        else:
            st.success("✅ **표준 도면 사양 (특이사항 없음)**")

    st.divider()

    # ---------------------------------------------------------
    # 4. [중단] 📋 핵심 제작 정보 요약 (층수 및 규격)
    # ---------------------------------------------------------
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

    # ---------------------------------------------------------
    # 5. [하단] 상세 리스트 (버튼 및 전체 명세)
    # ---------------------------------------------------------
    if all_tables:
        df_raw = pd.DataFrame(all_tables)
        header_idx = 0
        for i, row in df_raw.iterrows():
            if any(k in str(row.values) for k in ['품명', 'NAME', '사양', '자재내역']):
                header_idx = i; break
        df_raw.columns = df_raw.iloc[header_idx]
        df = df_raw.iloc[header_idx+1:].reset_index(drop=True).dropna(axis=1, how='all')

        st.markdown("---")
        st.subheader("🔘 버튼 투입 명세 (BUTTON LIST)")
        btn_mask = df.astype(str).apply(lambda x: x.str.contains('BUTTON|버튼|HIP|SJ21', case=False, na=False)).any(axis=1)
        btn_df = df[btn_mask]

        if not btn_df.empty:
            st.table(btn_df) 
        else:
            st.info("버튼 상세 항목을 찾지 못했습니다.")

        # NAME PLATE 별도 표시
        name_plate_mask = df.astype(str).apply(lambda x: x.str.contains('NAME PLATE|명판|NAMEPLATE', case=False, na=False)).any(axis=1)
        name_plate_df = df[name_plate_mask]
        if not name_plate_df.empty:
            st.markdown("#### 🏷️ NAME PLATE 상세 정보")
            st.table(name_plate_df)

        st.divider()
        st.subheader("📦 전체 자재 리스트")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.error("PDF 표 데이터를 읽을 수 없습니다.")
