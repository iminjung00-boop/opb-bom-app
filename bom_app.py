import streamlit as st
import pdfplumber
import pandas as pd
import re
import os

# 1. 페이지 설정 및 버전 정의
APP_VERSION = "V 1.5.5"
LAST_UPDATE = "2026.05.06"

# [수정] st.set_config -> st.set_page_config로 변경
st.set_page_config(page_title=f"SMC OPB BOM 시스템 {APP_VERSION}", layout="wide")

def show_updates():
    st.info(f"""
    **🚀 {APP_VERSION} 시스템 안정화 및 비표준 도면 확인 로직 통합 ({LAST_UPDATE})**
    * **오류 수정**: AttributeError를 일으켰던 함수 오타를 수정하여 시스템 복구[cite: 1]
    * **비표준 DWG 감지**: 자재 명세 내 '비표준', 'NON-STD' 포함 시 "도면 필수 확인" 경고 출력[cite: 1]
    * **로직 원복**: 사용자님이 요청하신 V 1.5.0의 가장 안정적인 데이터 추출 엔진 유지[cite: 1]
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

    # 2. 기본 정보 추출[cite: 1]
    project = re.search(r"공사명\s*[:\s]+([^\n]+)", all_text).group(1).strip() if "공사명" in all_text else "미확인"
    unit = re.search(r"호기번호\s*[:\s]+([A-Z0-9]+)", all_text).group(1).strip() if "호기번호" in all_text else "미확인"

    st.header(f"📊 {project} ({unit})")

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
        if '협력사' in df.columns: df = df.drop(columns=['협력사'])

        # 🔍 비표준 자재 감지 로직[cite: 1]
        non_std_items = []
        mask = df.astype(str).apply(lambda x: x.str.contains('비표준|NON-STD|NONSTD', case=False)).any(axis=1)
        if not df[mask].empty:
            non_std_items = df[mask]['자재내역'].tolist()

        # 📢 화면 출력 (주의사항 섹션)
        st.subheader("⚠️ 생산 핵심 주의사항")
        c_w1, c_w2 = st.columns(2)
        with c_w1:
            if non_std_items:
                st.error(f"🚫 **비표준 자재 감지: DWG 및 관련 도면을 반드시 참고하십시오.**")
                st.caption(f"대상 품목: {', '.join(non_std_items)}")
            
            parking_check = re.search(r"기준층\s*버튼\s*PARKING\s*SW\s*적용\s*\(([^)]+)\)", all_text)
            if parking_check and parking_check.group(1) != "미적용":
                st.error(f"🅿️ **기준층 PARKING SW 적용: {parking_check.group(1)}**")
        
        with c_w2:
            if "면취" in all_text: st.error("🔧 **DIS OPB 하부 면취가공 필수 (C0.5)**")
            if "비상통화장치" in all_text: st.error("🚨 **비상통화장치 적용 현장**")

        st.divider()

        # 📋 핵심 제작 사양 요약[cite: 1]
        m_c1, m_c2, m_c3 = st.columns([2, 1, 1]) 
        with m_c1: 
            t_floor = "미확인"
            a2_area = re.search(r"A2000.*?TOTAL\s*FLOOR(.*?)(?=FRONT\s*STOP\s*FLOOR|HX\s*1000|C2620|$)", all_text, re.DOTALL | re.IGNORECASE)
            if a2_area: t_floor = "TOTAL FLOOR " + re.sub(r'\s+', ' ', a2_area.group(1).strip()).strip()
            st.markdown(f"**🏢 전체 층수 정보 (TOTAL FLOOR)**")
            st.caption(t_floor) 
        with m_c2:
            b_floor = re.search(r"기준층\s*[:\s]*([0-9A-Z]+)", all_text)
            st.metric("📍 기준층 위치", b_floor.group(1).strip() if b_floor else "미확인")
        with m_c3:
            o_dir = re.search(r"열림방향(?:\(MAIN\))?\s*[:\s]*([가-힣A-Z/]+)", all_text)
            st.metric("🚪 열림방향", o_dir.group(1).strip() if o_dir else "미확인")

        st.divider()

        # 🎛️ OPB 상세 제작 사양[cite: 1]
        r1_c1, r1_c2, r1_c3, r1_c4 = st.columns(4)
        with r1_c1:
            opb_type = "정보 없음"
            type_f = re.search(r"OPB\s*([SD]\s*\d\s*\d\s*\d\s*[A-Z]?)", all_text, re.IGNORECASE)
            if type_f: opb_type = re.sub(r'\s+', '', type_f.group(1))
            st.info(f"✨ **OPB 타입**\n\n{opb_type}")
        
        with r1_c2:
            material_info = "정보 없음"
            lines = all_text.split('\n')
            for i, line in enumerate(lines):
                if "MATERIAL" in line.upper():
                    context = line + (lines[i+1] if i+1 < len(lines) else "")
                    mat_match = re.search(r"MATERIAL\s*[:\s]*([가-힣\s\-0-9A-Z\(\)]+)", context, re.IGNORECASE)
                    if mat_match:
                        material_info = f"* MATERIAL : {mat_match.group(1).strip()}"
                        break
            st.error(f"🎨 **표판 재질 사양**\n\n{material_info}") 
        
        with r1_c3: 
            b_size = re.search(r"BOX\s*[:\s]*([\d\s*xX,]{5,20})", all_text, re.IGNORECASE)
            st.info(f"📏 **BOX SIZE**\n\n{b_size.group(1).strip() if b_size else '정보 없음'}")
        with r1_c4: 
            d_no = re.search(r"S/W\s*PANEL.*?DWG\s*NO\.?\s*[:\s]*([0-9A-Z]+)", all_text, re.IGNORECASE | re.DOTALL)
            st.info(f"📄 **도면 번호**\n\n{d_no.group(1) if d_no else '정보 없음'}")

        st.divider()

        st.subheader("🔘 주요 자재 투입 명세 (핵심)")
        t_mask = df.astype(str).apply(lambda x: x.str.contains('BUTTON|버튼|HIP|SJ21|PCB|BOARD|E280|E281|E282', case=False, na=False)).any(axis=1)
        st.table(df[t_mask])

        st.subheader("📦 전체 자재 리스트")
        st.dataframe(df, use_container_width=True, hide_index=True)
