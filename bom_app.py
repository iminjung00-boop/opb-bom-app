import streamlit as st
import pdfplumber
import pandas as pd
import re
import os

# 1. 페이지 설정
st.set_page_config(page_title="SMC OPB생산 BOM통합 시스템 V 1.0", layout="wide")

if os.path.exists("logo.png"):
    st.image("logo.png", width=150)

st.title("SMC OPB생산 BOM통합 시스템 V 1.0")
st.write("비표준 사양, PCB 설정(IND/SD), BOX 규격 및 자재 명세를 통합 분석합니다.")

uploaded_file = st.file_uploader("분석할 BOM PDF 파일을 선택하세요 [cite: 1, 92]", type="pdf")

if uploaded_file:
    with pdfplumber.open(uploaded_file) as pdf:
        all_text = ""
        all_tables = []
        for page in pdf.pages:
            all_text += (page.extract_text() or "") + "\n"
            table = page.extract_table()
            if table:
                all_tables.extend(table)

    # 2. 기본 정보 추출 [cite: 2, 3, 93, 94]
    project = re.search(r"공사명\s*[:\s]+([^\n]+)", all_text).group(1).strip() if "공사명" in all_text else "미확인"
    unit = re.search(r"호기번호\s*[:\s]+([A-Z0-9]+)", all_text).group(1).strip() if "호기번호" in all_text else "미확인"

    st.header(f"📊 {project} ({unit})")

    # 3. 🚨 [최상단] 생산 핵심 주의사항 (비표준 사양 감지) 
    st.subheader("⚠️ 생산 핵심 주의사항 (FIRST CHECK)")
    
    opb_3t = "3t 적용" in all_text or "3T 적용" in all_text
    emergency_light = "비상통화장치 동작 표시등 적용" in all_text [cite: 85]
    open_dir_match = re.search(r"열림방향(?:\(MAIN\))?\s*[:\s]*([가-힣A-Z/]+)", all_text)
    open_direction = open_dir_match.group(1) if open_dir_match else "미확인" [cite: 177]
    
    col_warn1, col_warn2 = st.columns(2)
    with col_warn1:
        if opb_3t:
            st.error("🚨 **비표준 사양: OPB 표판 두께 3t 적용 (제작 주의)**") [cite: 189]
        st.warning(f"🚪 **열림방향(MAIN): {open_direction}**") [cite: 177]
        if emergency_light:
            st.error("🚨 **비상통화장치 동작 표시등 적용 현장**") [cite: 85]

    with col_warn2:
        if "면취" in all_text:
            st.error("🔧 **DIS OPB 하부 면취가공 필수 (C0.5)**")
        dwgs = re.findall(r"DWG\.?\s*([0-9A-Z]{7,10})", all_text)
        if dwgs:
            for d in set(dwgs): st.error(f"🚨 **비표준 도면 확인 필수: {d}**") [cite: 88, 179]
        else:
            st.success("✅ **표준 도면 사양 (특이사항 없음)**")

    st.divider()

    # 4. 🎛️ OPB 및 S/W PANEL 상세 제작 사양 (PCB 설정 포함) [cite: 156, 165, 170]
    st.subheader("🎛️ OPB 및 S/W PANEL 상세 제작 사양")
    
    # IND / SD 설정값 추출 [cite: 156]
    main_pcb_match = re.search(r"MAIN.*?OPB.*?(IN[D|V]:?[^,\n]+)", all_text, re.IGNORECASE)
    dis_pcb_match = re.search(r"DIS.*?OPB.*?(IN[D|V]:?[^,\n]+)", all_text, re.IGNORECASE)
    
    # BOX 규격 및 기타 사양 [cite: 165, 166]
    box_match = re.search(r"BOX\s*[:\s]*([\d\s*xX,]{5,20})", all_text, re.IGNORECASE)
    box_size_val = box_match.group(1).strip() if box_match else "정보 없음" [cite: 165]
    
    opb_spec = re.search(r"([SD]\d{3}[A-Z]?[,.]?\s*\d?DIGIT\.?[,.]?\s*G/S)", all_text, re.IGNORECASE)
    spec_val = opb_spec.group(1).strip() if opb_spec else "정보 없음" [cite: 82, 166]

    r1_c1, r1_c2, r1_c3 = st.columns(3)
    with r1_c1:
        st.info(f"✨ **OPB 타입/사양**\n\n{spec_val}") [cite: 82, 166]
    with r1_c2:
        st.info(f"📏 **MAIN BOX size**\n\n{box_size_val}") [cite: 165]
    with r1_c3:
        # PCB 설정값 (IND/SD) 표시 [cite: 156]
        st.success(f"🧩 **PCB 설정 (IND/SD)**\n\n{main_pcb_match.group(1).strip() if main_pcb_match else '정보 없음'}")

    r2_c1, r2_c2, r2_c3 = st.columns(3)
    with r2_c1:
        indicator_match = re.search(r"INDICATOR\s*DATA\s*[:\s]*([^\n]+)", all_text, re.IGNORECASE)
        st.info(f"📟 **인디케이터 문구**\n\n{indicator_match.group(1).strip() if indicator_match else '정보 없음'}") [cite: 25]
    with r2_c2:
        aircon_sw = "AIR-CON S/W 적용" in all_text [cite: 182]
        st.info(f"❄️ **에어컨 스위치:** {'적용' if aircon_sw else '미적용'}") [cite: 182]
    with r2_c3:
        skip_sw = "OWNER SKIP S/W 적용" in all_text [cite: 185]
        st.info(f"⏭️ **오너 스킵 스위치:** {'적용' if skip_sw else '미적용'}") [cite: 185]
    
    st.divider()

    # 5. 자재 리스트 분석 (표 데이터 복구) 
    if all_tables:
        df_raw = pd.DataFrame(all_tables)
        header_idx = 0
        for i, row in df_raw.iterrows():
            if any(k in str(row.values) for k in ['품명', 'NAME', '사양']):
                header_idx = i; break
        
        cols = list(df_raw.iloc[header_idx]); new_cols = []
        for i, val in enumerate(cols):
            val = str(val) if val else f"Unknown_{i}"
            if val in new_cols: new_cols.append(f"{val}_{i}")
            else: new_cols.append(val)
        df_raw.columns = new_cols
        df = df_raw.iloc[header_idx+1:].reset_index(drop=True).dropna(axis=1, how='all')

        st.subheader("🔘 버튼 및 자재 투입 명세")
        target_mask = df.astype(str).apply(lambda x: x.str.contains('BUTTON|버튼|HIP|PCB|BOARD|IOA', case=False, na=False)).any(axis=1)
        st.table(df[target_mask]) [cite: 72, 96]

        st.subheader("📦 전체 자재 리스트")
        st.dataframe(df, use_container_width=True, hide_index=True) [cite: 72, 96]
