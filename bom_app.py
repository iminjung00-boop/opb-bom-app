import streamlit as st
import pdfplumber
import pandas as pd
import re
import os

# 1. 페이지 설정
st.set_page_config(page_title="엘리베이터 BOM 통합 분석기", layout="wide")

# 로고 표시
if os.path.exists("logo.png"):
    st.image("logo.png", width=150)

st.title("🏭 엘리베이터 생산 BOM 통합 분석 시스템")
st.write("NAME PLATE 사양 및 전체 자재 명세를 자동으로 분석합니다.")

uploaded_file = st.file_uploader("분석할 BOM PDF 파일을 선택하세요", type="pdf")

if uploaded_file:
    with pdfplumber.open(uploaded_file) as pdf:
        all_text = ""
        all_tables = []
        for page in pdf.pages:
            all_text += page.extract_text() or ""
            table = page.extract_table()
            if table:
                all_tables.extend(table)

    # 2. 공사 정보 추출
    project = re.search(r"공사명\s*[:\s]+([^\n]+)", all_text).group(1).strip() if "공사명" in all_text else "현장명 미확인"
    unit = re.search(r"호기번호\s*[:\s]+([A-Z0-9]+)", all_text).group(1).strip() if "호기번호" in all_text else "호기 미확인"

    st.header(f"📊 {project} ({unit})")

    # 3. NAME PLATE 및 핵심 사양 집중 분석
    if all_tables:
        df_raw = pd.DataFrame(all_tables)
        header_idx = 0
        for i, row in df_raw.iterrows():
            if any(k in str(row.values) for k in ['품명', 'NAME', '사양', 'SPEC', '규격']):
                header_idx = i
                break
        df_raw.columns = df_raw.iloc[header_idx]
        df = df_raw.iloc[header_idx+1:].reset_index(drop=True).dropna(axis=1, how='all')

        st.subheader("📋 핵심 제작 사양 (NAME PLATE)")
        
        # --- NAME PLATE 정보만 필터링 ---
        # 품명 열에서 '명판'이나 'NAME PLATE'가 들어간 행 추출
        name_plate_mask = df.astype(str).apply(lambda x: x.str.contains('NAME PLATE|명판|NAMEPLATE', case=False, na=False)).any(axis=1)
        name_plate_df = df[name_plate_mask]

        col1, col2 = st.columns([2, 1])
        
        with col1:
            if not name_plate_df.empty:
                st.table(name_plate_df) # 명판 정보 강조
            else:
                st.info("BOM 리스트 내 별도의 NAME PLATE 항목을 찾지 못했습니다.")

        with col2:
            box_size = re.search(r"BOX\s*[:\s]*([\d\s*xX]+)", all_text)
            st.success(f"**BOX 규격:**\n\n{box_size.group(1) if box_size else '텍스트에서 확인 불가'}")
            material = "MIRROR" if "미러" in all_text or "MIRROR" in all_text else "HAIRLINE"
            st.warning(f"**표면 사양:**\n\nST'S {material}")

        st.divider()

        # 4. 전체 자재 리스트
        st.subheader("📦 전체 자재 명세 (NAME / SPEC / SIZE)")
        st.dataframe(df, use_container_width=True, hide_index=True)
        
    else:
        st.error("PDF 표 데이터를 읽을 수 없습니다.")
