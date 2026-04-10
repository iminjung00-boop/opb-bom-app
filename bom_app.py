import streamlit as st
import pdfplumber
import pandas as pd
import re
import os

# 1. 페이지 설정 (브라우저 탭 아이콘 및 제목)
st.set_page_config(
    page_title="엘리베이터 BOM 통합 분석기", 
    page_icon="🏢", # 여기에 로고 파일 경로를 넣을 수도 있습니다.
    layout="wide"
)

# --- 회사 로고 넣기 ---
# 폴더에 logo.png 파일이 있다면 상단에 표시합니다.
if os.path.exists("logo.png"):
    st.image("logo.png", width=200) 
else:
    st.sidebar.warning("로고 파일을 찾을 수 없습니다 (logo.png를 폴더에 넣어주세요)")

st.title("OPB 생산 BOM 통합 관리 시스템")
st.write("PDF를 업로드하면 공사명, 버튼 수량, 주의사항을 자동으로 정리합니다.")

uploaded_file = st.file_uploader("BOM PDF 파일을 업로드하세요", type="pdf")

if uploaded_file:
    with pdfplumber.open(uploaded_file) as pdf:
        all_text = ""
        all_tables = []
        for page in pdf.pages:
            all_text += page.extract_text()
            table = page.extract_table()
            if table:
                all_tables.extend(table)

    # 2. 데이터 자동 추출 (범용 로직)
    project_name = "미확인"
    project_match = re.search(r"공사명\s*[:\s]+([^\n]+)", all_text)
    if project_match: project_name = project_match.group(1).strip()

    unit_no = "미확인"
    unit_match = re.search(r"호기번호\s*[:\s]+([A-Z0-9]+)", all_text)
    if unit_match: unit_no = unit_match.group(1).strip()

    st.header(f"📊 분석 결과: {project_name} ({unit_no})")

    # 3. 상세 자재 및 버튼 리스트 (표 분석)
    st.subheader("📦 주요 자재 및 버튼 리스트")
    if all_tables:
        df = pd.DataFrame(all_tables)
        header_index = 0
        for i, row in df.iterrows():
            if any(k in str(row.values) for k in ['자재내역', 'PART', '자재번호']):
                header_index = i
                break
        
        df.columns = df.iloc[header_index]
        df = df.iloc[header_index+1:].reset_index(drop=True)

        # 생산 필수 키워드 필터링
        keywords = ['BUTTON', 'HIP', 'OPB', 'CABLE', 'HARNESS', 'PI-', '버튼']
        mask = df.astype(str).apply(lambda x: x.str.contains('|'.join(keywords), case=False, na=False)).any(axis=1)
        display_df = df[mask].dropna(axis=1, how='all')

        if not display_df.empty:
            st.dataframe(display_df, use_container_width=True) # 깔끔한 인터랙티브 표
        else:
            st.info("상세 표 데이터를 분석 중입니다.")
    else:
        st.warning("표 데이터를 찾을 수 없습니다.")

    # 4. 생산 주의사항 자동 감지 (수천 개 현장 공용)
    st.divider()
    st.subheader("⚠️ 생산 주의사항 (자동 감지)")
    
    # 비표준 도면 번호 (일동미라주의 28012359 등 자동 감지)
    dwg_nos = re.findall(r"DWG\.?\s*([0-9A-Z]{7,10})", all_text)
    if dwg_nos:
        for dwg in set(dwg_nos):
            st.error(f"🚨 비표준 도면 확인 필수: {dwg}")
    
    # 텍스트 기반 지시사항 감지
    warnings = {
        "면취가공": "🔧 DIS OPB 하부 면취가공(C0.5) 필수!",
        "열림/닫힘 버튼 하부": "🔘 벨버튼 위치 주의: [열림/닫힘] 하단 배치",
        "한국어": "🔊 음성 안내: 한국어 시스템 적용"
    }

    for key, msg in warnings.items():
        if key in all_text:
            st.warning(msg)
        