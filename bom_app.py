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
st.write("PCB 취부 사양(IND/SD) 및 BOX 규격을 실시간으로 분석합니다.")

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

    # 3. 🚨 [최상단] 생산 핵심 주의사항
    st.subheader("⚠️ 생산 핵심 주의사항 (FIRST CHECK)")
    
    opb_3t = "3t 적용" in all_text or "3T 적용" in all_text
    emergency_light = "비상통화장치 동작 표시등 적용" in all_text
    
    col_warn1, col_warn2 = st.columns(2)
    with col_warn1:
        if opb_3t:
            st.error("🚨 **비표준 사양: OPB 표판 두께 3t 적용 (제작 주의)**")
        if emergency_light:
            st.error("🚨 **비상통화장치 동작 표시등 적용 현장**")
    with col_warn2:
        if "면취" in all_text:
            st.error("🔧 **DIS OPB 하부 면취가공 필수 (C0.5)**")

    st.divider()

    # ---------------------------------------------------------
    # 4. 🧩 PCB 취부 상세 사양 (IND / SD 판별)
    # ---------------------------------------------------------
    st.subheader("🧩 PCB 취부 상세 사양 (IND / SD)")
    
    # IND, SD 값 추출 (X, O, 0 등 대응)
    ind_match = re.search(r"IND\s*[:\s]*([XO0])", all_text, re.IGNORECASE)
    sd_match = re.search(r"SD\s*[:\s]*([XO0])", all_text, re.IGNORECASE)
    
    ind_val = ind_match.group(1).upper() if ind_match else "미확인"
    sd_val = sd_match.group(1).upper() if sd_match else "미확인"

    # 취부 여부 메시지 생성
    def get_status(val):
        if val in ['O', '0']: return "✅ 취부 필수"
        if val == 'X': return "❌ 취부 제외 (삭제)"
        return "❓ 확인 필요"

    c_ind, c_sd = st.columns(2)
    with c_ind:
        st.metric(label="📟 인디케이터 (IND)", value=ind_val, delta=get_status(ind_val), delta_color="normal")
    with c_sd:
        st.metric(label="🔢 세그먼트 (SD)", value=sd_val, delta=get_status(sd_val), delta_color="normal")

    st.divider()

    # 5. 🎛️ OPB 및 S/W PANEL 상세 제작 사양
    st.subheader("🎛️ OPB 및 S/W PANEL 상세 제작 사양")
    
    box_pattern = re.compile(r"BOX\s*[:\s]*([\d\s*xX,]{5,20})", re.IGNORECASE)
    box_match = box_pattern.search(all_text)
    box_size_val = box_match.group(1).strip() if box_match else "정보 없음"

    sw_dwg_pattern = re.compile(r"S/W\s*PANEL.*?DWG\s*NO\.?\s*[:\s]*([0-9A-Z]+)", re.IGNORECASE | re.DOTALL)
    sw_panel_dwg = sw_dwg_pattern.search(all_text)
    
    r1_c1, r1_c2, r1_c3 = st.columns(3)
    with r1_c1:
        st.info(f"📏 **MAIN BOX size**\n\n{box_size_val}")
    with r1_c2:
        st.info(f"📄 **S/W PANEL 도면**\n\n{sw_panel_dwg.group(1) if sw_panel_dwg else '정보 없음'}")
    with r1_c3:
        indicator_match = re.search(r"INDICATOR\s*DATA\s*[:\s]*([^\n]+)", all_text, re.IGNORECASE)
        st.info(f"📟 **인디케이터 문구**\n\n{indicator_match.group(1).strip() if indicator_match else '정보 없음'}")

    st.divider()

    # 6. 자재 리스트
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

        st.subheader("🔘 버튼 및 주요 자재 투입 명세")
        target_mask = df.astype(str).apply(lambda x: x.str.contains('BUTTON|버튼|HIP|PCB|BOARD|IOA', case=False, na=False)).any(axis=1)
        st.table(df[target_mask])
