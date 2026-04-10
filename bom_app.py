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
st.write("층수(TOTAL FLOOR) 및 버튼 구성을 자동으로 추출하여 생산 실수를 방지합니다.")

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

    # 2. 공사 정보 추출
    project = re.search(r"공사명\s*[:\s]+([^\n]+)", all_text).group(1).strip() if "공사명" in all_text else "현장명 미확인"
    unit = re.search(r"호기번호\s*[:\s]+([A-Z0-9]+)", all_text).group(1).strip() if "호기번호" in all_text else "호기 미확인"

    st.header(f"📊 {project} ({unit})")

    # 3. 🚨 생산 핵심 주의사항
    st.subheader("⚠️ 생산 핵심 주의사항")
    
    # 열림방향 및 TOTAL FLOOR 추출
    open_dir_match = re.search(r"열림방향(?:\(MAIN\))?\s*[:\s]*([가-힣A-Z/]+)", all_text)
    open_direction = open_dir_match.group(1) if open_dir_match else "미확인"
    
    floor_match = re.search(r"TOTAL\s*FLOOR\s*[:\s]*([\d\/\s]+F?)", all_text, re.IGNORECASE)
    total_floor = floor_match.group(1).strip() if floor_match else "미확인"

    dwgs = re.findall(r"DWG\.?\s*([0-9A-Z]{7,10})", all_text)
    
    col_warn1, col_warn2 = st.columns(2)
    with col_warn1:
        st.warning(f"🚪 **열림방향(MAIN):** {open_direction}")
        if "면취" in all_text:
            st.warning("🔧 **DIS OPB 하부 면취가공 사양 포함**")
            
    with col_warn2:
        if dwgs:
            for d in set(dwgs):
                st.error(f"🚨 **비표준 도면 확인 필수:** {d}")
        else:
            st.success("✅ **표준 도면 사양 (특이사항 없음)**")

    st.divider()

    # 4. 📋 핵심 제작 요약 (TOTAL FLOOR 강조)
    if all_tables:
        df_raw = pd.DataFrame(all_tables)
        header_idx = 0
        for i, row in df_raw.iterrows():
            if any(k in str(row.values) for k in ['품명', 'NAME', '사양', 'SPEC']):
                header_idx = i; break
        df_raw.columns = df_raw.iloc[header_idx]
        df = df_raw.iloc[header_idx+1:].reset_index(drop=True).dropna(axis=1, how='all')

        st.subheader("📋 핵심 제작 사양 요약")
        c1, c2, c3, c4 = st.columns(4)
        
        box_size = re.search(r"BOX\s*[:\s]*([\d\s*xX]+)", all_text)
        material = "MIRROR" if any(k in all_text for k in ["미러", "MIRROR"]) else "HAIRLINE"
        
        with c1:
            st.metric("🏢 TOTAL FLOOR", total_floor, help="전체 층수 정보")
        with c2:
            st.metric("📏 BOX 규격", box_size.group(1) if box_size else "미확인")
        with c3:
            st.metric("✨ 표면 사양", f"ST'S {material}")
        with c4:
            st.metric("🚪 열림방향", open_direction)

        # 5. 🔘 [신규] 버튼 구성 정보 집중 분석
        st.markdown("---")
        st.subheader("🔘 버튼 구성 정보 (BUTTON LIST)")
        
        # 품명에 'BUTTON' 또는 '버튼'이 들어간 행만 추출
        btn_mask = df.astype(str).apply(lambda x: x.str.contains('BUTTON|버튼|BTN', case=False, na=False)).any(axis=1)
        btn_df = df[btn_mask]

        if not btn_df.empty:
            # 버튼 정보를 더 강조하기 위해 배경색이 있는 표나 컨테이너 사용
            st.info(f"💡 이 현장은 총 **{total_floor}** 층이며, 아래 버튼들이 투입됩니다.")
            st.dataframe(btn_df, use_container_width=True, hide_index=True)
        else:
            st.info("자재 명세 내에서 버튼 정보를 별도로 찾지 못했습니다. 아래 전체 명세를 확인하세요.")

        # 6. NAME PLATE 상세
        name_plate_mask = df.astype(str).apply(lambda x: x.str.contains('NAME PLATE|명판|NAMEPLATE', case=False, na=False)).any(axis=1)
        name_plate_df = df[name_plate_mask]
        if not name_plate_df.empty:
            st.markdown("#### 🏷️ NAME PLATE 상세 정보")
            st.table(name_plate_df)

        st.divider()

        # 7. 전체 자재 리스트
        st.subheader("📦 전체 자재 명세 (전체 리스트)")
        st.dataframe(df, use_container_width=True, hide_index=True)
        
    else:
        st.error("PDF 표 데이터를 읽을 수 없습니다.")
