import streamlit as st
import pdfplumber
import pandas as pd
import re
import os

# 1. 페이지 설정
st.set_page_config(page_title="엘리베이터 BOM 통합 분석기", layout="wide")

if os.path.exists("logo.png"):
    st.image("logo.png", width=150)

st.title("🏭 엘리베이터 생산 BOM 통합 분석 시스템")
st.write("비상통화장치 유무를 포함한 모든 명판(NAME PLATE) 상세 사양을 통합 분석합니다.")

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

    # 2. 공사 정보 추출
    project = re.search(r"공사명\s*[:\s]+([^\n]+)", all_text).group(1).strip() if "공사명" in all_text else "미확인"
    unit = re.search(r"호기번호\s*[:\s]+([A-Z0-9]+)", all_text).group(1).strip() if "호기번호" in all_text else "미확인"

    st.header(f"📊 {project} ({unit})")

    # 3. 🚨 [최상단] 생산 핵심 주의사항
    st.subheader("⚠️ 생산 핵심 주의사항 (FIRST CHECK)")
    
    # 주요 키워드 감지
    emergency_light = "비상통화장치 동작 표시등 적용" in all_text
    fireman_sw = "FIREMAN STICKER: YES" in all_text or "비상용" in all_text
    open_dir_match = re.search(r"열림방향(?:\(MAIN\))?\s*[:\s]*([가-힣A-Z/]+)", all_text)
    open_direction = open_dir_match.group(1) if open_dir_match else "미확인"
    dwgs = re.findall(r"DWG\.?\s*([0-9A-Z]{7,10})", all_text)
    
    col_warn1, col_warn2 = st.columns(2)
    with col_warn1:
        st.warning(f"🚪 **열림방향(MAIN): {open_direction}**")
        if emergency_light:
            st.error("🚨 **비상통화장치 동작 표시등 적용 현장**")
        if fireman_sw:
            st.error("🔥 **비상용 엘리베이터 (FIREMAN STICKER 적용)**")

    with col_warn2:
        if dwgs:
            for d in set(dwgs):
                st.error(f"🚨 **비표준 도면 확인 필수: {d}**")
        else:
            st.success("✅ **표준 도면 사양 (특이사항 없음)**")

    st.divider()

    # 4. 📋 핵심 제작 정보 요약 (층수/규격)
    st.subheader("📋 핵심 제작 사양 요약")
    floor_match = re.search(r"TOTAL\s*FLOOR\s*[:\s]*([^\n]+)", all_text, re.IGNORECASE)
    total_floor_detail = floor_match.group(1).strip() if floor_match else "미확인"
    box_size = re.search(r"BOX\s*[:\s]*([\d\s*xX]+)", all_text)
    material = "MIRROR" if any(k in all_text for k in ["미러", "MIRROR"]) else "HAIRLINE"

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("🏢 전체 층수 (TOTAL)", total_floor_detail)
    with c2:
        st.metric("📏 BOX 규격", box_size.group(1) if box_size else "미확인")
    with c3:
        st.metric("✨ 표면 사양", f"ST'S {material}")

    # 5. [강화된 섹션] NAME PLATE 상세 사양 통합
    st.markdown("---")
    st.subheader("🏷️ NAME PLATE 상세 제작 사양")
    
    # 텍스트에서 명판 관련 세부 정보 추출
    person_match = re.search(r"인승\s*[:\s]*([\d]+)\s*인승", all_text)
    weight_match = re.search(r"용량\s*[:\s]*([\d]+)\s*kg", all_text)
    voice_match = "VOICE SYNTHESIZER" in all_text or "음성안내" in all_text
    
    col_np1, col_np2 = st.columns(2)
    
    with col_np1:
        st.write(f"👥 **인승/용량:** {person_match.group(0) if person_match else '정보 없음'} / {weight_match.group(0) if weight_match else ''}")
        st.write(f"📢 **음성 안내:** {'적용 (한국어)' if voice_match else '미적용'}")
        st.write(f"🔥 **비상용 스티커:** {'YES (FIREMAN)' if fireman_sw else 'NO'}")

    with col_np2:
        # 비상통화장치 유무 강조
        if emergency_light:
            st.error("🚨 **비상통화장치 동작 표시등: 적용**")
        else:
            st.success("✅ **비상통화장치 동작 표시등: 미적용**")
        
        # 비상통화장치 종류 표시
        intercom_match = re.search(r"비상통화장치\s*[:\s]*([^\n]+)", all_text)
        st.write(f"📞 **통화장치 종류:** {intercom_match.group(1) if intercom_match else '정보 없음'}")

    # 6. 버튼 및 전체 리스트 (하단 배치)
    if all_tables:
        df_raw = pd.DataFrame(all_tables)
        header_idx = 0
        for i, row in df_raw.iterrows():
            if any(k in str(row.values) for k in ['품명', 'NAME', '사양']):
                header_idx = i; break
        
        cols = list(df_raw.iloc[header_idx])
        new_cols = []
        for i, val in enumerate(cols):
            val = str(val) if val else f"Unknown_{i}"
            if val in new_cols: new_cols.append(f"{val}_{i}")
            else: new_cols.append(val)
        df_raw.columns = new_cols
        df = df_raw.iloc[header_idx+1:].reset_index(drop=True).dropna(axis=1, how='all')

        st.subheader("🔘 버튼 투입 명세")
        btn_mask = df.astype(str).apply(lambda x: x.str.contains('BUTTON|버튼|HIP|SJ21', case=False, na=False)).any(axis=1)
        st.table(df[btn_mask])

        st.divider()
        st.subheader("📦 전체 자재 리스트")
        st.dataframe(df, use_container_width=True, hide_index=True)
