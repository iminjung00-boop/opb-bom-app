import streamlit as st
import pdfplumber
import pandas as pd
import re
import os

# 1. 페이지 설정 및 버전 정의
APP_VERSION = "V 1.5.1"
LAST_UPDATE = "2026.04.15"

st.set_page_config(page_title=f"SMC OPB BOM 시스템 {APP_VERSION}", layout="wide")

def show_updates():
    st.info(f"""
    **🚀 {APP_VERSION} 주요 제작 사양 감지 로직 복구 및 강화**
    * **특수 두께 감지**: 표판 두께가 **3T 이상**일 경우 주의사항에 강조 표시
    * **특수 공정 감지**: '에칭(Etching)', '카운터(Counter)' 등 별도 가공 사양 감지 추가
    * **로직 안정화**: 가장 안정적인 V 1.4.3 엔진을 기반으로 주의사항 로직만 정밀 보강
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

    # 2. 기본 정보 추출
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

        if '협력사' in df.columns:
            df = df.drop(columns=['협력사'])

        # ---------------------------------------------------------
        # 3. 데이터 정밀 추출 및 특수 사양 감지
        # ---------------------------------------------------------
        
        # (1) 층수 정보
        total_floors_display = "미확인"
        a2000_area = re.search(r"A2000.*?TOTAL\s*FLOOR(.*?)(?=FRONT\s*STOP\s*FLOOR|HX\s*1000|C2620|$)", all_text, re.DOTALL | re.IGNORECASE)
        if a2000_area:
            raw_floors = a2000_area.group(1).strip()
            total_floors_display = "TOTAL FLOOR " + re.sub(r'\s+', ' ', raw_floors).strip()

        # (2) MATERIAL 및 두께(3T) 감지
        material_info = "정보 없음"
        thick_alert = False
        etching_alert = False
        
        lines = all_text.split('\n')
        for i, line in enumerate(lines):
            if "MATERIAL" in line.upper():
                context = line + (lines[i+1] if i+1 < len(lines) else "")
                mat_match = re.search(r"MATERIAL\s*[:\s]*([가-힣\s\-0-9A-Z\(\)]+)", context, re.IGNORECASE)
                if mat_match:
                    found_mat = mat_match.group(1).strip()
                    material_info = f"* MATERIAL : {found_mat}"
                    # 두께 3T 이상 감지
                    if re.search(r"[3-9]\s*[tT]", found_mat) or "3T" in found_mat.upper():
                        thick_alert = True
                    # 에칭 가공 감지
                    if "에칭" in found_mat or "ETCHING" in found_mat.upper():
                        etching_alert = True
                    break

        # (3) 인승/용량 및 기타 사양
        person_match = re.search(r"(\d+)\s*인승", all_text)
        capacity_match = re.search(r"(\d+)\s*kg", all_text)
        name_plate_info = f"{person_match.group(1)}인승 / {capacity_match.group(1)}kg" if person_match and capacity_match else "미확인"
        
        # 4. 화면 출력
        st.subheader("⚠️ 생산 핵심 주의사항")
        c_w1, c_w2 = st.columns(2)
        with c_w1:
            # 두께 및 에칭 경고문 추가
            if thick_alert:
                st.error("📐 **두께 주의: 표판 두께 3T 이상 사양입니다. (절곡/가공 확인)**")
            if etching_alert:
                st.error("🎨 **특수 공정: 에칭(ETCHING) 가공이 포함된 사양입니다.**")
            
            parking_check = re.search(r"기준층\s*버튼\s*PARKING\s*SW\s*적용\s*\(([^)]+)\)", all_text)
            if parking_check and parking_check.group(1) != "미적용":
                st.error(f"🅿️ **기준층 PARKING SW 적용: {parking_check.group(1)}**")
        
        with c_w2:
            if "면취" in all_text: st.error("🔧 **DIS OPB 하부 면취가공 필수 (C0.5)**")
            if "비상통화장치" in all_text: st.error("🚨 **비상통화장치 적용 현장**")
            if "COUNTER" in all_text.upper(): st.error("🔢 **카운터(COUNTER) 표시 사양 확인 필요**")

        st.divider()

        # [나머지 UI 레이아웃은 V 1.4.3과 동일하게 유지]
        st.subheader("📋 핵심 제작 사양 요약")
        m_c1, m_c2, m_c3 = st.columns([2, 1, 1]) 
        with m_c1: 
            st.markdown(f"**🏢 전체 층수 정보 (TOTAL FLOOR)**")
            st.caption(total_floors_display) 
        with m_c2:
            base_floor_match = re.search(r"기준층\s*[:\s]*([0-9A-Z]+)", all_text)
            st.metric("📍 기준층 위치", base_floor_match.group(1).strip() if base_floor_match else "미확인")
        with m_c3:
            open_dir_match = re.search(r"열림방향(?:\(MAIN\))?\s*[:\s]*([가-힣A-Z/]+)", all_text)
            st.metric("🚪 열림방향", open_dir_match.group(1).strip() if open_dir_match else "미확인")

        st.info(f"👥 **인승/용량:** {name_plate_info}")

        st.divider()

        st.subheader("🎛️ OPB 및 PCB 상세 제작 사양")
        r1_c1, r1_c2, r1_c3, r1_c4 = st.columns(4)
        with r1_c1:
            opb_spec = "정보 없음"
            target_row = df[df.astype(str).apply(lambda x: x.str.contains('E280A')).any(axis=1)]
            if not target_row.empty:
                spec_find = re.search(r"OPB\s*([SD]\s*\d\s*\d\s*\d\s*[A-Z]?)", str(target_row.values), re.IGNORECASE)
                if spec_find: opb_spec = re.sub(r'\s+', '', spec_find.group(1))
            st.info(f"✨ **OPB 타입**\n\n{opb_spec}")
        with r1_c2: st.error(f"🎨 **표판 재질 사양**\n\n{material_info}") 
        with r1_c3: 
            box_match = re.search(r"BOX\s*[:\s]*([\d\s*xX,]{5,20})", all_text, re.IGNORECASE)
            st.info(f"📏 **BOX SIZE**\n\n{box_match.group(1).strip() if box_match else '정보 없음'}")
        with r1_c4: 
            sw_dwg = re.search(r"S/W\s*PANEL.*?DWG\s*NO\.?\s*[:\s]*([0-9A-Z]+)", all_text, re.IGNORECASE | re.DOTALL)
            st.info(f"📄 **도면 번호**\n\n{sw_dwg.group(1) if sw_dwg else '정보 없음'}")

        st.divider()

        st.subheader("🔘 주요 자재 투입 명세 (핵심)")
        target_mask = df.astype(str).apply(lambda x: x.str.contains('BUTTON|버튼|HIP|SJ21|PCB|BOARD|E280|E281|E282', case=False, na=False)).any(axis=1)
        st.table(df[target_mask])

        st.subheader("📦 전체 자재 리스트")
        st.dataframe(df, use_container_width=True, hide_index=True)
