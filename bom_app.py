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
st.write("BOM 내의 상세 층수(FLOOR)와 버튼 구성을 정밀하게 추출합니다.")

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

    # 2. 정보 추출 (포에스프라자 예시 기준)
    project = re.search(r"공사명\s*[:\s]+([^\n]+)", all_text).group(1).strip() if "공사명" in all_text else "미확인"
    unit = re.search(r"호기번호\s*[:\s]+([A-Z0-9]+)", all_text).group(1).strip() if "호기번호" in all_text else "미확인"

    # 3. 상세 층수 및 열림방향 추출
    # 예: B2,B1.1,2,3,4,5,6 형태 대응
    floor_match = re.search(r"TOTAL\s*FLOOR\s*[:\s]*([^\n]+)", all_text, re.IGNORECASE)
    total_floor_detail = floor_match.group(1).strip() if floor_match else "미확인"
    
    open_dir_match = re.search(r"열림방향(?:\(MAIN\))?\s*[:\s]*([가-힣A-Z/]+)", all_text)
    open_direction = open_dir_match.group(1) if open_dir_match else "미확인"

    st.header(f"📊 {project} ({unit})")

    # 4. 🚨 상단 핵심 요약 대시보드
    st.subheader("📌 핵심 제작 정보 요약")
    c1, c2, c3, c4 = st.columns(4)
    
    box_size = re.search(r"BOX\s*[:\s]*([\d\s*xX]+)", all_text)
    material = "MIRROR" if any(k in all_text for k in ["미러", "MIRROR"]) else "HAIRLINE"
    
    with c1:
        st.metric("🏢 전체 층수", total_floor_detail)
    with c2:
        st.metric("📏 BOX 규격", box_size.group(1) if box_size else "미확인")
    with c3:
        st.metric("✨ 표면 재질", f"ST'S {material}")
    with c4:
        st.metric("🚪 열림방향", open_direction)

    st.divider()

    # 5. 🔘 버튼 구성 및 수량 정보 (HIP 집중 분석)
    if all_tables:
        df_raw = pd.DataFrame(all_tables)
        header_idx = 0
        for i, row in df_raw.iterrows():
            if any(k in str(row.values) for k in ['품명', 'NAME', '사양', '자재내역']):
                header_idx = i; break
        df_raw.columns = df_raw.iloc[header_idx]
        df = df_raw.iloc[header_idx+1:].reset_index(drop=True).dropna(axis=1, how='all')

        st.subheader("🔘 버튼 투입 명세 (BUTTON LIST)")
        # HIP, BUTTON, SJ21D 등 버튼 관련 키워드 필터링
        btn_mask = df.astype(str).apply(lambda x: x.str.contains('BUTTON|버튼|HIP|SJ21', case=False, na=False)).any(axis=1)
        btn_df = df[btn_mask]

        if not btn_df.empty:
            st.success(f"✅ 이 현장은 **{total_floor_detail}** 구성이며, 총 {len(btn_df)}종류의 버튼이 확인됩니다.")
            st.table(btn_df) # 버튼 정보는 가독성을 위해 고정된 표(table)로 표시
        else:
            st.info("BOM 표 내에서 버튼 상세 항목을 찾지 못했습니다.")

        # 6. 생산 주의사항
        st.divider()
        st.subheader("⚠️ 생산 주의사항")
        col_err1, col_err2 = st.columns(2)
        
        with col_err1:
            dwgs = re.findall(r"DWG\.?\s*([0-9A-Z]{7,10})", all_text)
            if dwgs:
                for d in set(dwgs): st.error(f"🚨 비표준 도면 확인: {d}")
            if "면취" in all_text: st.warning("🔧 DIS OPB 하부 면취가공 필수 (C0.5)")
        
        with col_err2:
            if "벨버튼" in all_text: st.warning("🔘 벨버튼 위치: [열림/닫힘] 하단 배치")
            if "차입식" in all_text: st.info("📎 설치 방식: 차입식 브라켓 적용")

        # 7. 전체 자재 리스트
        st.divider()
        st.subheader("📦 전체 자재 리스트")
        st.dataframe(df, use_container_width=True, hide_index=True)
