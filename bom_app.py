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
st.write("BOM에 기재된 실제 BOX 규격을 실시간으로 추출하여 표시합니다.")

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
    st.subheader("⚠️ 생산 핵심 주의사항 (비표준 사양 감지)")
    
    opb_3t = "3t 적용" in all_text or "3T 적용" in all_text
    emergency_light = "비상통화장치 동작 표시등 적용" in all_text
    open_dir_match = re.search(r"열림방향(?:\(MAIN\))?\s*[:\s]*([가-힣A-Z/]+)", all_text)
    open_direction = open_dir_match.group(1) if open_dir_match else "미확인"
    
    col_warn1, col_warn2 = st.columns(2)
    with col_warn1:
        if opb_3t:
            st.error("🚨 **비표준 사양: OPB 표판 두께 3t 적용 (제작 주의)**")
        st.warning(f"🚪 **열림방향(MAIN): {open_direction}**")
        if emergency_light:
            st.error("🚨 **비상통화장치 동작 표시등 적용 현장**")

    with col_warn2:
        if "면취" in all_text:
            st.error("🔧 **DIS OPB 하부 면취가공 필수 (C0.5)**")
        dwgs = re.findall(r"DWG\.?\s*([0-9A-Z]{7,10})", all_text)
        if dwgs:
            for d in set(dwgs): st.error(f"🚨 **비표준 도면 확인 필수: {d}**")
        else:
            st.success("✅ **표준 도면 사양 (특이사항 없음)**")

    st.divider()

    # ---------------------------------------------------------
    # 4. 🎛️ OPB 및 S/W PANEL 상세 제작 사양
    # ---------------------------------------------------------
    st.subheader("🎛️ OPB 및 S/W PANEL 상세 제작 사양")
    
    # [핵심 수정] 이미지 사양(BOX: 164 x 1704)을 정확히 추출하는 정규식
    # 숫자, x, X, *, 공백, 콤마 등을 모두 포함하여 규격 전체를 가져옵니다.
    box_pattern = re.compile(r"BOX\s*[:\s]*([\d\s*xX,]{5,20})", re.IGNORECASE)
    box_match = box_pattern.search(all_text)
    box_size_val = box_match.group(1).strip() if box_match else "정보 없음"

    # S521A 등 사양 추출
    opb_spec_pattern = re.compile(r"([SD]\d{3}[A-Z]?[,.]?\s*\d?DIGIT\.?[,.]?\s*G/S|[SD]\d{3}[A-Z]{1,2})", re.IGNORECASE)
    opb_spec_search = opb_spec_pattern.search(all_text)
    opb_type_text = opb_spec_search.group(1).strip() if opb_spec_search else "정보 없음"
    
    sw_dwg_pattern = re.compile(r"S/W\s*PANEL.*?DWG\s*NO\.?\s*[:\s]*([0-9A-Z]+)", re.IGNORECASE | re.DOTALL)
    sw_panel_dwg = sw_dwg_pattern.search(all_text)
    
    indicator_match = re.search(r"INDICATOR\s*DATA\s*[:\s]*([^\n]+)", all_text, re.IGNORECASE)
    indicator_text = indicator_match.group(1).strip() if indicator_match else "정보 없음"
    
    # 레이아웃 배치
    r1_c1, r1_c2, r1_c3 = st.columns(3)
    with r1_c1:
        st.info(f"✨ **OPB 타입/사양 (INDICATOR)**\n\n{opb_type_text}")
    with r1_c2:
        # 여기에 164 x 1704 와 같은 값이 들어갑니다.
        st.info(f"📏 **MAIN BOX size**\n\n{box_size_val}")
    with r1_c3:
        st.info(f"📄 **S/W PANEL 도면 (BOM 필수 확인)**\n\n{sw_panel_dwg.group(1) if sw_panel_dwg else '정보 없음'}")

    r2_c1, r2_c2, r2_c3 = st.columns(3)
    with r2_c1:
        st.info(f"📟 **인디케이터 표시 문구**\n\n{indicator_text}")
    with r2_c2:
        aircon_sw = "AIR-CON S/W 적용" in all_text or "에어컨" in all_text
        st.info(f"❄️ **에어컨 스위치:** {'적용' if aircon_sw else '미적용'}")
    with r2_c3:
        skip_sw = "OWNER SKIP S/W 적용" in all_text or "오너스킵" in all_text
        st.info(f"⏭️ **오너 스킵 스위치:** {'적용' if skip_sw else '미적용'}")
    
    st.divider()

    # 5. 핵심 제작 정보 요약
    st.subheader("📋 핵심 제작 사양 요약")
    floor_match = re.search(r"TOTAL\s*FLOOR\s*[:\s]*([^\n]+)", all_text, re.IGNORECASE)
    material = "MIRROR" if any(k in all_text for k in ["미러", "MIRROR"]) else "HAIRLINE"

    c_m1, c_m2, c_m3 = st.columns(3)
    with c_m1:
        st.metric("🏢 전체 층수 (TOTAL)", floor_match.group(1).strip() if floor_match else "미확인")
    with c_m2:
        st.metric("📏 MAIN BOX size (확인)", box_size_val)
    with c_m3:
        st.metric("✨ 표면 사양", f"ST'S {material}")

    # 6. 자재 리스트 분석
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

        st.subheader("🔘 버튼 투입 명세")
        btn_mask = df.astype(str).apply(lambda x: x.str.contains('BUTTON|버튼|HIP|SJ21', case=False, na=False)).any(axis=1)
        st.table(df[btn_mask])

        st.subheader("📦 전체 자재 리스트")
        st.dataframe(df, use_container_width=True, hide_index=True)
