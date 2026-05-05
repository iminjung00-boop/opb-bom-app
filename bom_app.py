import streamlit as st
import pdfplumber
import pandas as pd
import re
import os

# 1. 페이지 설정 및 버전 정의
APP_VERSION = "V 1.5.3"
LAST_UPDATE = "2026.05.05"

st.set_page_config(page_title=f"SMC OPB BOM 시스템 {APP_VERSION}", layout="wide")

def show_updates():
    st.info(f"""
    **🚀 {APP_VERSION} 모든 특수 사양 감지 로직 완전 통합 ({LAST_UPDATE})**
    * **비표준/NON-STD 전수 조사**: 자재 명세 내 모든 비표준 사양 자동 검출
    * **제작 공정 정밀 감지**: 표판 두께(3T 이상), 에칭(Etching), 카운터(Counter) 등 특수 사양 복구
    * **UI 최적화**: 가장 피드백이 좋았던 V 1.4.3의 레이아웃 기반으로 모든 기능 집대성
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

    # 기본 정보 추출[cite: 1]
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

        # ---------------------------------------------------------
        # 🔍 전체 문서 전수 조사 (특수 사양 감지)
        # ---------------------------------------------------------
        
        # (1) 비표준 자재 감지[cite: 1]
        non_std_items = []
        non_std_mask = df.astype(str).apply(lambda x: x.str.contains('비표준|NON-STD|NONSTD', case=False)).any(axis=1)
        if not df[non_std_mask].empty:
            non_std_items = df[non_std_mask]['자재내역'].tolist()

        # (2) 제작 사양 정밀 스캔 (두께, 에칭, 카운터)
        material_info = "정보 없음"
        thick_alert = False
        etching_alert = False
        counter_alert = "COUNTER" in all_text.upper()
        
        lines = all_text.split('\n')
        for i, line in enumerate(lines):
            if "MATERIAL" in line.upper():
                context = line + (lines[i+1] if i+1 < len(lines) else "")
                mat_match = re.search(r"MATERIAL\s*[:\s]*([가-힣\s\-0-9A-Z\(\)]+)", context, re.IGNORECASE)
                if mat_match:
                    found_mat = mat_match.group(1).strip()
                    material_info = f"* MATERIAL : {found_mat}"
                    # 두께 3T 감지
                    if re.search(r"[3-9]\s*[tT]", found_mat) or "3T" in found_mat.upper(): thick_alert = True
                    # 에칭 감지
                    if any(k in found_mat for k in ["에칭", "ETCHING"]): etching_alert = True
                    break

        # ---------------------------------------------------------
        # 📢 화면 출력 (주의사항 섹션)
        # ---------------------------------------------------------
        st.subheader("⚠️ 생산 핵심 주의사항")
        c_w1, c_w2 = st.columns(2)
        with c_w1:
            if non_std_items: st.error(f"🚫 **비표준 자재 포함:** {', '.join(non_std_items)}")[cite: 1]
            if thick_alert: st.error("📐 **두께 주의: 표판 두께 3T 이상 사양 (절곡 확인)**")
            if etching_alert: st.error("🎨 **특수 공정: 에칭(ETCHING) 가공 확인**")
            if counter_alert: st.error("🔢 **카운터(COUNTER) 표시 사양 포함**")
        
        with c_w2:
            parking_check = re.search(r"기준층\s*버튼\s*PARKING\s*SW\s*적용\s*\(([^)]+)\)", all_text)
            if parking_check and parking_check.group(1) != "미적용":
                st.error(f"🅿️ **기준층 PARKING SW 적용: {parking_check.group(1)}**")
            if "면취" in all_text: st.error("🔧 **DIS OPB 하부 면취가공 필수 (C0.5)**")
            if "비상통화장치" in all_text: st.error("🚨 **비상통화장치 적용 현장**")

        st.divider()

        # 📋 핵심 제작 사양 요약
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

        # 🎛️ OPB 및 PCB 상세 제작 사양
        r1_c1, r1_c2, r1_c3, r1_c4 = st.columns(4)
        with r1_c1:
            opb_type = "정보 없음"
            type_f = re.search(r"OPB\s*([SD]\s*\d\s*\d\s*\d\s*[A-Z]?)", all_text, re.IGNORECASE)
            if type_f: opb_type = re.sub(r'\s+', '', type_f.group(1))
            st.info(f"✨ **OPB 타입**\n\n{opb_type}")
        with r1_c2: st.error(f"🎨 **표판 재질 사양**\n\n{material_info}") 
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
