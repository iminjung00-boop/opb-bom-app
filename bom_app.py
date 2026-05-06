import streamlit as st
import pdfplumber
import pandas as pd
import re
import os

# 1. 페이지 설정 및 버전 정의
APP_VERSION = "V 1.6.2"
LAST_UPDATE = "2026.05.06"

st.set_page_config(page_title=f"SMC OPB BOM 시스템 {APP_VERSION}", layout="wide")

def show_updates():
    st.info(f"""
    **🚀 {APP_VERSION} 에어컨 및 PCB 상세 사양 UI 복구 ({LAST_UPDATE})**
    * **PCB 옵션 정밀 추출**: E280A16 블록에서 GT.MAIN 등 상세 PCB 사양 추출 로직 복구
    * **에어컨/오너스킵**: 문서 내 키워드를 감지하여 적용 여부를 대시보드에 표시
    * **에러 원천 차단**: 이전 버전의 텍스트 스캔 방식을 유지하여 TypeError 방지
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
            content = page.extract_text() or ""
            all_text += content + "\n"
            table = page.extract_table()
            if table:
                all_tables.extend(table)

    # 2. 기본 정보 추출[cite: 1]
    project = re.search(r"공사명\s*[:\s]+([^\n]+)", all_text).group(1).strip() if "공사명" in all_text else "미확인"
    unit = re.search(r"호기번호\s*[:\s]+([A-Z0-9]+)", all_text).group(1).strip() if "호기번호" in all_text else "미확인"

    st.header(f"📊 {project} ({unit})")

    # 🔍 현장 도면 지시 사항 추출 (V 1.6.1 로직)[cite: 1]
    dwg_instructions = []
    matches = re.findall(r"([^\.\n]*(?:MAIN|DIS)\s*OPB는\s*현장\s*도면\s*DWG\.\s*[0-9]+\s*참고하여\s*제작[^\.\n]*)", all_text)
    if matches:
        dwg_instructions = list(set([m.strip() for m in matches]))

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
        # 3. 데이터 정밀 추출 로직 (V 1.5.0 기반 복구)[cite: 1]
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

        # (3) PCB 옵션 및 에어컨 적용 여부[cite: 1]
        pcb_option = "정보 없음"
        pcb_row = df[df.astype(str).apply(lambda x: x.str.contains('E280A16')).any(axis=1)]
        if not pcb_row.empty:
            pcb_text = " ".join(pcb_row.values.flatten().astype(str)).replace('\n', '')
            pcb_match = re.search(r"(GT[\s,.]*MAIN.*?G/S)", pcb_text, re.IGNORECASE)
            if pcb_match: pcb_option = re.sub(r'\s+', ' ', pcb_match.group(1)).strip()

        aircon = "✅ 적용" if any(k in all_text.upper() for k in ["AIR-CON", "에어컨"]) else "❌ 미적용"
        skip_sw = "✅ 적용" if any(k in all_text.upper() for k in ["SKIP S/W", "오너스킵"]) else "❌ 미적용"

        # 4. 화면 출력 (주의사항)[cite: 1]
        st.subheader("⚠️ 생산 핵심 주의사항")
        c_w1, c_w2 = st.columns(2)
        with c_w1:
            if dwg_instructions:
                for ins in dwg_instructions:
                    st.error(f"📐 **제작 지침: {ins}**")
            
            parking_check = re.search(r"기준층\s*버튼\s*PARKING\s*SW\s*적용\s*\(([^)]+)\)", all_text)
            if parking_check and parking_check.group(1) != "미적용":
                st.error(f"🅿️ **기준층 PARKING SW 적용: {parking_check.group(1)}**")
        
        with c_w2:
            if "면취가공" in all_text: st.error("🔧 **하부 면취가공 필수 (C0.5)**")
            if "비상통화장치" in all_text: st.error("🚨 **비상통화장치 적용 현장**")

        st.divider()

        # 핵심 사양 요약[cite: 1]
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

        st.divider()

        # 🎛️ 상세 제작 사양 (에어컨/PCB 복구)[cite: 1]
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
            sw_d = re.search(r"S/W\s*PANEL.*?DWG\s*NO\.?\s*[:\s]*([0-9A-Z]+)", all_text, re.IGNORECASE | re.DOTALL)
            st.info(f"📄 **도면 번호**\n\n{sw_d.group(1) if sw_d else '정보 없음'}")

        # [추가된 PCB/에어컨 대시보드][cite: 1]
        r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)
        with r2_c1:
            indicator_match = re.search(r"INDICATOR\s*DATA\s*[:\s]*([^\n]+)", all_text, re.IGNORECASE)
            st.info(f"📟 **인디케이터**\n\n{indicator_match.group(1).strip() if indicator_match else '정보 없음'}")
        with r2_c2: st.warning(f"🔋 **PCB 옵션**\n\n{pcb_option}")
        with r2_c3: st.success(f"❄️ **에어컨:** {aircon}")
        with r2_c4: st.success(f"⏭️ **오너스킵:** {skip_sw}")

        st.divider()

        st.subheader("🔘 주요 자재 투입 명세 (핵심)")
        target_mask = df.astype(str).apply(lambda x: x.str.contains('BUTTON|버튼|HIP|SJ21|PCB|BOARD|E280|E281|E282', case=False, na=False)).any(axis=1)
        st.table(df[target_mask])

        st.subheader("📦 전체 자재 리스트")
        st.dataframe(df, use_container_width=True, hide_index=True)
