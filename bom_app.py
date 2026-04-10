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
st.write("BOM의 취부 사양(O/X)과 자재 명세를 동시에 분석하여 제작 오류를 방지합니다.")

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

    # 3. 🚨 생산 핵심 주의사항 (상단 배치)
    st.subheader("⚠️ 생산 핵심 주의사항")
    opb_3t = "3t 적용" in all_text or "3T 적용" in all_text
    emergency_light = "비상통화장치 동작 표시등 적용" in all_text
    
    col_warn1, col_warn2 = st.columns(2)
    with col_warn1:
        if opb_3t: st.error("🚨 **비표준 사양: OPB 표판 두께 3t 적용**")
        if emergency_light: st.error("🚨 **비상통화장치 동작 표시등 적용 현장**")
    with col_warn2:
        if "면취" in all_text: st.error("🔧 **DIS OPB 하부 면취가공 필수 (C0.5)**")

    st.divider()

    # ---------------------------------------------------------
    # 4. 🧩 PCB 취부 상세 사양 (IND / SD O,X 판별)
    # ---------------------------------------------------------
    st.subheader("🧩 PCB 취부 상세 사양 (O: 취부 필수 / X: 취부 제외)")
    
    # IND, SD 값 추출 (예: IND:X.SD:0.G/S) 
    main_pcb = re.search(r"MAIN.*?OPB.*?(IND:?[XO0]).*?(SD:?[XO0])", all_text, re.IGNORECASE)
    dis_pcb = re.search(r"DIS.*?OPB.*?(IND:?[XO0]).*?(SD:?[XO0])", all_text, re.IGNORECASE)

    def get_display_val(match, index):
        if not match: return "미확인"
        val = match.group(index).split(':')[-1].upper().replace('0', 'O')
        return val

    def get_status_msg(val):
        if val == 'O': return "✅ 취부 필수 (조립)"
        if val == 'X': return "❌ 취부 제외 (삭제)"
        return "정보 없음"

    row_pcb_1, row_pcb_2 = st.columns(2)
    with row_pcb_1:
        st.markdown("#### [메인 OPB]")
        m_ind = get_display_val(main_pcb, 1)
        m_sd = get_display_val(main_pcb, 2)
        st.metric("IND (인디케이터)", m_ind, get_status_msg(m_ind))
        st.metric("SD (세그먼트)", m_sd, get_status_msg(m_sd))
    
    with row_pcb_2:
        st.markdown("#### [장애자용 OPB]")
        d_ind = get_display_val(dis_pcb, 1)
        d_sd = get_display_val(dis_pcb, 2)
        st.metric("IND (인디케이터)", d_ind, get_status_msg(d_ind))
        st.metric("SD (세그먼트)", d_sd, get_status_msg(d_sd))

    st.divider()

    # 5. 🎛️ 제작 상세 규격
    st.subheader("🎛️ 제작 상세 규격")
    box_match = re.search(r"BOX\s*[:\s]*([\d\s*xX,]{5,20})", all_text, re.IGNORECASE)
    sw_dwg = re.search(r"S/W\s*PANEL.*?DWG\s*NO\.?\s*[:\s]*([0-9A-Z]+)", all_text, re.IGNORECASE)
    indicator_data = re.search(r"INDICATOR\s*DATA\s*[:\s]*([^\n]+)", all_text, re.IGNORECASE)

    c1, c2, c3 = st.columns(3)
    with c1: st.info(f"📏 **MAIN BOX size**\n\n{box_match.group(1).strip() if box_match else '정보 없음'}")
    with c2: st.info(f"📄 **S/W PANEL 도면**\n\n{sw_dwg.group(1) if sw_dwg else '정보 없음'}")
    with c3: st.info(f"📟 **인디케이터 문구**\n\n{indicator_data.group(1).strip() if indicator_data else '정보 없음'}")

    st.divider()

    # 6. 자재 리스트 (복구 완료)
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

        st.subheader("🔘 자재 투입 명세")
        target_mask = df.astype(str).apply(lambda x: x.str.contains('BUTTON|버튼|HIP|PCB|BOARD|IOA', case=False, na=False)).any(axis=1)
        st.table(df[target_mask])
