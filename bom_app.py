import streamlit as st
import pdfplumber
import pandas as pd
import re
import os

# 1. 페이지 설정 및 버전 정의
APP_VERSION = "V 1.5.8"
LAST_UPDATE = "2026.05.06"

st.set_page_config(page_title=f"SMC OPB BOM 시스템 {APP_VERSION}", layout="wide")

def show_updates():
    st.info(f"""
    **🚀 {APP_VERSION} 블록별 현장 도면(DWG) 제작 지시 사항 완벽 연동 ({LAST_UPDATE})**
    * **지시 사항 강제 추출**: BLOCK E280A, E281A 하단에 위치한 "현장 도면 참고 제작" 문구를 전수 조사하여 주의사항에 표출
    * **안정성 유지**: 사용자님이 신뢰하시는 V 1.5.0 추출 엔진을 기반으로 데이터 신뢰도 확보
    * **데이터 통합**: 층수(FRONT STOP), 재질(* MATERIAL :), 인승/용량 등 기존 성공 로직 보존
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

        # ---------------------------------------------------------
        # 🔍 [신규] BLOCK E280A / E281A 현장 도면 지시 사항 추출
        # ---------------------------------------------------------
        dwg_instructions = []
        
        # E280A 및 E281A 블록 내에서 "현장 도면" 또는 "DWG" 문구 포함 행 검색[cite: 1]
        target_blocks = ['E280A', 'E281A']
        for block in target_blocks:
            block_rows = df[df.astype(str).apply(lambda x: x.str.contains(block)).any(axis=1)]
            if not block_rows.empty:
                # 해당 블록 데이터 전체를 텍스트로 합쳐서 도면 지시 사항 검색[cite: 1]
                block_content = " ".join(block_rows.astype(str).values.flatten())
                # "현장 도면 DWG. 숫자 참고하여 제작" 패턴 매칭
                match = re.search(r"([^\.]*(?:MAIN|DIS)\s*OPB는\s*현장\s*도면\s*DWG\.\s*[0-9]+\s*참고하여\s*제작[^\.]*)", block_content)
                if match:
                    dwg_instructions.append(match.group(1).strip())

        # ---------------------------------------------------------
        # 3. 데이터 정밀 추출 로직 (V 1.5.0 기반)[cite: 1]
        # ---------------------------------------------------------
        
        # (1) A2000 층수 정보
        total_floors_display = "미확인"
        a2000_area = re.search(r"A2000.*?TOTAL\s*FLOOR(.*?)(?=FRONT\s*STOP\s*FLOOR|HX\s*1000|C2620|$)", all_text, re.DOTALL | re.IGNORECASE)
        if a2000_area:
            total_floors_display = "TOTAL FLOOR " + re.sub(r'\s+', ' ', a2000_area.group(1).strip()).strip()

        # (2) MATERIAL 재질 정보
        material_info = "정보 없음"
        for line in all_text.split('\n'):
            if "MATERIAL" in line.upper():
                mat_match = re.search(r"MATERIAL\s*[:\s]*([가-힣\s\-0-9A-Z\(\)]+)", line, re.IGNORECASE)
                if mat_match:
                    material_info = f"* MATERIAL : {mat_match.group(1).strip()}"
                    break

        # 4. 화면 출력 (주의사항 강화)[cite: 1]
        st.subheader("⚠️ 생산 핵심 주의사항")
        c_w1, c_w2 = st.columns(2)
        with c_w1:
            # [추가] 추출된 현장 도면 지시 사항 강조
            if dwg_instructions:
                for ins in dwg_instructions:
                    st.error(f"📐 **제작 지시: {ins}**")
            else:
                st.info("기본 제작 사양에 따라 제작하십시오.")
            
            parking_check = re.search(r"기준층\s*버튼\s*PARKING\s*SW\s*적용\s*\(([^)]+)\)", all_text)
            if parking_check and parking_check.group(1) != "미적용":
                st.error(f"🅿️ **기준층 PARKING SW 적용: {parking_check.group(1)}**")
        
        with c_w2:
            if "면취가공" in all_text: st.error("🔧 **하부 면취가공 필수 (C0.5)**")
            if "비상통화장치" in all_text: st.error("🚨 **비상통화장치 적용 현장**")

        st.divider()

        # 핵심 제작 사양 요약[cite: 1]
        m_c1, m_c2, m_c3 = st.columns([2, 1, 1]) 
        with m_c1: 
            st.markdown(f"**🏢 전체 층수 정보 (TOTAL FLOOR)**")
            st.caption(total_floors_display) 
        with m_c2:
            base_f = re.search(r"기준층\s*[:\s]*([0-9A-Z]+)", all_text)
            st.metric("📍 기준층 위치", base_f.group(1).strip() if base_f else "미확인")
        with m_c3:
            open_d = re.search(r"열림방향(?:\(MAIN\))?\s*[:\s]*([가-힣A-Z/]+)", all_text)
            st.metric("🚪 열림방향", open_d.group(1).strip() if open_d else "미확인")

        st.info(f"👥 **인승/용량:** {re.search(r'(\d+)\s*인승', all_text).group(1) if re.search(r'(\d+)\s*인승', all_text) else '?'}인승 / {re.search(r'(\d+)\s*kg', all_text).group(1) if re.search(r'(\d+)\s*kg', all_text) else '?'}kg")

        st.divider()

        # 🎛️ 상세 제작 사양[cite: 1]
        r1_c1, r1_c2, r1_c3, r1_c4 = st.columns(4)
        with r1_c1:
            opb_spec = "정보 없음"
            type_f = re.search(r"OPB\s*([SD]\s*\d\s*\d\s*\d\s*[A-Z]?)", all_text, re.IGNORECASE)
            if type_f: opb_spec = re.sub(r'\s+', '', type_f.group(1))
            st.info(f"✨ **OPB 타입**\n\n{opb_spec}")
        with r1_c2: st.error(f"🎨 **표판 재질 사양**\n\n{material_info}") 
        with r1_c3: 
            box_s = re.search(r"BOX\s*[:\s]*([\d\s*xX,]{5,20})", all_text, re.IGNORECASE)
            st.info(f"📏 **BOX SIZE**\n\n{box_s.group(1).strip() if box_s else '정보 없음'}")
        with r1_c4: 
            sw_d = re.search(r"S/W\s*PANEL.*?DWG\s*NO\.?\s*[:\s]*([0-9A-Z]+)", all_text, re.IGNORECASE | re.DOTALL)
            st.info(f"📄 **도면 번호**\n\n{sw_d.group(1) if sw_d else '정보 없음'}")

        st.divider()

        st.subheader("🔘 주요 자재 투입 명세 (핵심)")
        target_mask = df.astype(str).apply(lambda x: x.str.contains('BUTTON|버튼|HIP|SJ21|PCB|BOARD|E280|E281|E282', case=False, na=False)).any(axis=1)
        st.table(df[target_mask])

        st.subheader("📦 전체 자재 리스트")
        st.dataframe(df, use_container_width=True, hide_index=True)
