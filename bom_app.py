import streamlit as st
import pdfplumber
import pandas as pd
import re
import os

# 1. 페이지 설정 및 버전 정의
APP_VERSION = "V 1.1.2"
LAST_UPDATE = "2026.04.10"

st.set_page_config(page_title=f"SMC OPB BOM 시스템 {APP_VERSION}", layout="wide")

# [업데이트 사항 표기 기능]
def show_updates():
    st.info(f"""
    **🚀 {APP_VERSION} 업데이트 안내 ({LAST_UPDATE})**
    * **기준층 정보 정밀화**: TOTAL FLOOR 및 기준층(Parking) 위치 자동 추출 기능 복구 
    * **취부 사양 판별**: 에어컨 및 오너스킵 S/W 취부 여부 시각적 강조 추가 
    * **자재 리스트 복구**: 하단에 원본 '전체 자재 리스트' 섹션을 다시 배치 
    * **필터링 보강**: E280, E281 등 주요 관리 파트 번호 누락 방지 로직 적용 
    """)

if os.path.exists("logo.png"):
    st.image("logo.png", width=150)

st.title(f"SMC OPB생산 BOM통합 시스템 {APP_VERSION}")

# 업데이트 사항 상단 노출
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

    # 2. 정보 추출 (공사명: 포에스프라자 등)
    project = re.search(r"공사명\s*[:\s]+([^\n]+)", all_text).group(1).strip() if "공사명" in all_text else "미확인" [cite: 2, 12]
    unit = re.search(r"호기번호\s*[:\s]+([A-Z0-9]+)", all_text).group(1).strip() if "호기번호" in all_text else "미확인" [cite: 1, 11]

    st.header(f"📊 {project} ({unit})")

    # 3. 🚨 생산 핵심 주의사항
    st.subheader("⚠️ 생산 핵심 주의사항")
    parking_match = re.search(r"기준층\s*버튼\s*PARKING\s*SW\s*적용\s*\(([^)]+)\)", all_text) [cite: 7]
    parking_val = parking_match.group(1) if parking_match else "미적용"
    opb_3t = "3t 적용" in all_text or "3T 적용" in all_text
    
    col_warn1, col_warn2 = st.columns(2)
    with col_warn1:
        if parking_val != "미적용":
            st.error(f"🅿️ **기준층 PARKING SW 적용: {parking_val} (제작 주의)**")
        if opb_3t: st.error("🚨 **비표준 사양: OPB 표판 두께 3t 적용**")
    with col_warn2:
        if "면취" in all_text: st.error("🔧 **DIS OPB 하부 면취가공 필수 (C0.5)**") [cite: 25]
        if "비상통화장치" in all_text: st.error("🚨 **비상통화장치 동작 표시등 적용 현장**") [cite: 25]

    st.divider()

    # 4. 📋 핵심 제작 사양 요약
    st.subheader("📋 핵심 제작 사양 요약")
    floor_info_match = re.search(r"TOTAL\s*FLOOR\s*[:\s]*([0-9A-Z,\s]+)", all_text, re.IGNORECASE) [cite: 7]
    total_floors = floor_info_match.group(1).strip() if floor_info_match else "미확인"
    base_floor_match = re.search(r"기준층\s*[:\s]*([0-9A-Z]+)", all_text) [cite: 7]
    base_floor = base_floor_match.group(1).strip() if base_floor_match else "미확인"

    c_m1, c_m2, c_m3 = st.columns(3)
    with c_m1: st.metric("🏢 전체 층수 (TOTAL)", total_floors)
    with c_m2: st.metric("📍 기준층 위치", base_floor)
    with c_m3: 
        material = "MIRROR" if any(k in all_text for k in ["미러", "MIRROR"]) else "HAIRLINE" [cite: 25]
        st.metric("✨ 표면 재질", f"ST'S {material}")

    st.divider()

    # 5. 🎛️ OPB 상세 사양
    st.subheader("🎛️ OPB 및 S/W PANEL 상세 사양")
    opb_spec_pattern = re.compile(r"([SD]\d{3}[A-Z]?[,.]?\s*\d?DIGIT\.?[,.]?\s*G/S|[SD]\d{3}[A-Z]{1,2})", re.IGNORECASE) [cite: 7]
    opb_spec_search = opb_spec_pattern.search(all_text)
    opb_type_text = opb_spec_search.group(1).strip() if opb_spec_search else "정보 없음"
    
    box_match = re.search(r"BOX\s*[:\s]*([\d\s*xX,]{5,20})", all_text, re.IGNORECASE) [cite: 7, 25]
    sw_dwg = re.search(r"S/W\s*PANEL.*?DWG\s*NO\.?\s*[:\s]*([0-9A-Z]+)", all_text, re.IGNORECASE | re.DOTALL) [cite: 25]
    
    r1_c1, r1_c2, r1_c3 = st.columns(3)
    with r1_c1: st.info(f"✨ **OPB 타입/사양 (INDICATOR)**\n\n{opb_type_text}")
    with r1_c2: st.info(f"📏 **MAIN BOX size**\n\n{box_match.group(1).strip() if box_match else '정보 없음'}")
    with r1_c3: st.info(f"📄 **S/W PANEL 도면**\n\n{sw_dwg.group(1) if sw_dwg else '정보 없음'}")

    aircon_sw = any(k in all_text for k in ["AIR-CON S/W", "에어컨"])
    skip_sw = any(k in all_text for k in ["SKIP S/W", "오너스킵"])
    indicator_data = re.search(r"INDICATOR\s*DATA\s*[:\s]*([^\n]+)", all_text, re.IGNORECASE) [cite: 7]

    r2_c1, r2_c2, r2_c3 = st.columns(3)
    with r2_c1: st.success(f"❄️ **에어컨 S/W 취부:** {'✅ 적용' if aircon_sw else '❌ 미적용'}")
    with r2_c2: st.success(f"⏭️ **오너스킵 S/W 취부:** {'✅ 적용' if skip_sw else '❌ 미적용'}")
    with r2_c3: st.info(f"📟 **인디케이터 문구**\n\n{indicator_data.group(1).strip() if indicator_data else '정보 없음'}")

    st.divider()

    # 6. 자재 리스트 (필터 및 전체 리스트)
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

        st.subheader("🔘 주요 자재 투입 명세 (필터링)")
        target_mask = df.astype(str).apply(lambda x: x.str.contains('BUTTON|버튼|HIP|SJ21|PCB|BOARD|E280|E281|E282|E291', case=False, na=False)).any(axis=1) [cite: 25]
        st.table(df[target_mask])
        
        st.subheader("📦 전체 자재 리스트 (원본 전체 데이터)")
        st.dataframe(df, use_container_width=True, hide_index=True)
