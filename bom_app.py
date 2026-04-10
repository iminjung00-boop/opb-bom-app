import streamlit as st
import pdfplumber
import pandas as pd
import re
import os

# 1. 페이지 설정
st.set_page_config(page_title="SMC OPB생산 BOM통합 시스템 V 1.1", layout="wide")

if os.path.exists("logo.png"):
    st.image("logo.png", width=150)

st.title("SMC OPB생산 BOM통합 시스템 V 1.1")
st.write("기준층 파킹, 에어컨/오너스킵 취부 사양을 포함한 통합 분석 도구입니다.")

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

    # 3. 🚨 생산 핵심 주의사항
    st.subheader("⚠️ 생산 핵심 주의사항")
    
    # [기준층 정보] 포에스프라자(SJ210) 등 기준층 파킹 스위치 추출
    parking_match = re.search(r"기준층\s*버튼\s*PARKING\s*SW\s*적용\s*\(([^)]+)\)", all_text)
    parking_val = parking_match.group(1) if parking_match else "미적용"
    
    opb_3t = "3t 적용" in all_text or "3T 적용" in all_text
    emergency_light = "비상통화장치 동작 표시등 적용" in all_text
    
    col_warn1, col_warn2 = st.columns(2)
    with col_warn1:
        if parking_val != "미적용":
            st.error(f"🅿️ **기준층 PARKING SW 적용: {parking_val} (제작 주의)**")
        if opb_3t: st.error("🚨 **비표준 사양: OPB 표판 두께 3t 적용**")
    with col_warn2:
        if "면취" in all_text: st.error("🔧 **DIS OPB 하부 면취가공 필수 (C0.5)**")
        if emergency_light: st.error("🚨 **비상통화장치 동작 표시등 적용 현장**")

    st.divider()

    # 4. 🎛️ 제작 상세 규격 요약
    st.subheader("📋 핵심 제작 사양 요약")
    
    # 전체 층수 정보
    floor_match = re.search(r"TOTAL\s*FLOOR\s*([^\n,]+)", all_text, re.IGNORECASE)
    floor_val = floor_match.group(1).strip() if floor_match else "미확인"
    material = "MIRROR" if any(k in all_text for k in ["미러", "MIRROR"]) else "HAIRLINE"

    c_m1, c_m2, c_m3 = st.columns(3)
    with c_m1: st.metric("🏢 전체 층수 (TOTAL)", floor_val)
    with c_m2: st.metric("📍 기준층(Parking)", parking_val)
    with c_m3: st.metric("✨ 표면 재질", f"ST'S {material}")

    st.divider()

    # 5. 🛠️ OPB 취부 및 옵션 상세 사양
    st.subheader("🎛️ OPB 및 S/W PANEL 상세 사양")
    
    box_match = re.search(r"BOX\s*[:\s]*([\d\s*xX,]{5,20})", all_text, re.IGNORECASE)
    sw_dwg = re.search(r"S/W\s*PANEL.*?DWG\s*NO\.?\s*[:\s]*([0-9A-Z]+)", all_text, re.IGNORECASE | re.DOTALL)
    
    # [옵션 정보] 에어컨, 오너스킵 취부 여부
    aircon_sw = any(k in all_text for k in ["AIR-CON S/W 적용", "에어컨"])
    skip_sw = any(k in all_text for k in ["OWNER SKIP S/W 적용", "오너스킵"])
    voice_sw = "VOICE SYNTHESIZER" in all_text

    r1_c1, r1_c2, r1_c3 = st.columns(3)
    with r1_c1: st.info(f"📏 **MAIN BOX size**\n\n{box_match.group(1).strip() if box_match else '정보 없음'}")
    with r1_c2: st.info(f"📄 **S/W PANEL 도면**\n\n{sw_dwg.group(1) if sw_dwg else '정보 없음'}")
    with r1_c3: st.info(f"📟 **음성 가이드**\n\n{'적용(한국어)' if voice_sw else '미적용'}")

    r2_c1, r2_c2, r2_c3 = st.columns(3)
    with r2_c1: 
        st.success(f"❄️ **에어컨 S/W 취부**\n\n{'✅ 적용' if aircon_sw else '❌ 미적용'}")
    with r2_c2:
        st.success(f"⏭️ **오너스킵 S/W 취부**\n\n{'✅ 적용' if skip_sw else '❌ 미적용'}")
    with r2_c3:
        indicator_data = re.search(r"INDICATOR\s*DATA\s*[:\s]*([^\n]+)", all_text, re.IGNORECASE)
        st.info(f"📟 **인디케이터 표시**\n\n{indicator_data.group(1).strip() if indicator_data else '정보 없음'}")

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

        st.subheader("🔘 자재 투입 명세")
        target_mask = df.astype(str).apply(lambda x: x.str.contains('BUTTON|버튼|HIP|SJ21|PCB|BOARD|E280A|E281A', case=False, na=False)).any(axis=1)
        st.table(df[target_mask])
