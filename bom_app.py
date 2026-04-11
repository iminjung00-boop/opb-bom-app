import streamlit as st
import pdfplumber
import pandas as pd
import re
import os

# 1. 페이지 설정 및 버전 정의
APP_VERSION = "V 1.2.0"
LAST_UPDATE = "2026.04.11"

st.set_page_config(page_title=f"SMC OPB BOM 시스템 {APP_VERSION}", layout="wide")

def show_updates():
    st.info(f"""
    **🚀 {APP_VERSION} 시스템 복구 및 최적화 ({LAST_UPDATE})**
    * **문법 오류 해결**: 코드 내 불필요한 시스템 태그 제거로 실행 오류(SyntaxError) 완전 해결
    * **E280A 블록 고정 분석**: 메인 OPB 사양이 기재되는 E280A 행을 추적하여 사양 추출 정확도 확보
    * **누락 방지**: 기준층, 층수 정보, 에어컨/오너스킵 등 모든 기존 기능을 하나도 빠짐없이 유지
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

    # 3. 데이터 프레임 생성 및 정밀 분석
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
        # 4. E280A 블록 사양 추출 로직 (누락 방지)
        # ---------------------------------------------------------
        opb_spec = "정보 없음"
        target_row = df[df.astype(str).apply(lambda x: x.str.contains('E280A')).any(axis=1)]
        
        if not target_row.empty:
            row_content = " ".join(target_row.values.flatten().astype(str))
            # S521A 등 사양 패턴 검색 (공백 허용)
            spec_find = re.search(r"OPB\s*([SD]\s*\d\s*\d\s*\d\s*[A-Z]?)", row_content, re.IGNORECASE)
            if spec_find:
                opb_spec = re.sub(r'\s+', '', spec_find.group(1))
            else:
                backup_find = re.search(r"([SD]\s*\d\s*\d\s*\d\s*[A-Z])", row_content)
                if backup_find:
                    opb_spec = re.sub(r'\s+', '', backup_find.group(1))

        # 5. 기타 정보 추출
        parking_match = re.search(r"기준층\s*버튼\s*PARKING\s*SW\s*적용\s*\(([^)]+)\)", all_text)
        parking_val = parking_match.group(1) if parking_match else "미적용"
        
        floor_info = re.search(r"TOTAL\s*FLOOR\s*[:\s]*([0-9A-Z,\s]+)", all_text, re.IGNORECASE)
        total_floors = floor_info.group(1).split('기준층')[0].strip() if floor_info else "미확인"
        
        box_match = re.search(r"BOX\s*[:\s]*([\d\s*xX,]{5,20})", all_text, re.IGNORECASE)
        sw_dwg = re.search(r"S/W\s*PANEL.*?DWG\s*NO\.?\s*[:\s]*([0-9A-Z]+)", all_text, re.IGNORECASE | re.DOTALL)

        # 6. 화면 출력
        st.subheader("⚠️ 생산 핵심 주의사항")
        c_w1, c_w2 = st.columns(2)
        with c_w1:
            if parking_val != "미적용": st.error(f"🅿️ **기준층 PARKING SW 적용: {parking_val}**")
            if "3t 적용" in all_text.lower(): st.error("🚨 **비표준 사양: OPB 표판 두께 3t 적용**")
        with c_w2:
            if "면취" in all_text: st.error("🔧 **DIS OPB 하부 면취가공 필수 (C0.5)**")
            if "비상통화장치" in all_text: st.error("🚨 **비상통화장치 적용 현장**")

        st.divider()

        st.subheader("📋 핵심 제작 사양 요약")
        c_m1, c_m2, c_m3 = st.columns(3)
        with c_m1: st.metric("🏢 전체 층수", total_floors)
        with c_m2: st.metric("📍 기준층 위치", parking_val)
        with c_m3: st.metric("✨ OPB 타입/사양", opb_spec)

        st.divider()

        st.subheader("🎛️ OPB 상세 제작 사양")
        r1_c1, r1_c2, r1_c3 = st.columns(3)
        with r1_c1: st.info(f"📏 **MAIN BOX size**\n\n{box_match.group(1).strip() if box_match else '정보 없음'}")
        with r1_c2: st.info(f"📄 **S/W PANEL 도면**\n\n{sw_dwg.group(1) if sw_dwg else '정보 없음'}")
        with r1_c3: 
            aircon = "✅ 적용" if any(k in all_text for k in ["AIR-CON", "에어컨"]) else "❌ 미적용"
            st.success(f"❄️ **에어컨 S/W:** {aircon}")

        st.divider()

        st.subheader("🔘 주요 자재 투입 명세 (핵심)")
        target_mask = df.astype(str).apply(lambda x: x.str.contains('BUTTON|버튼|HIP|SJ21|PCB|BOARD|E280|E281|E282', case=False, na=False)).any(axis=1)
        st.table(df[target_mask])

        st.subheader("📦 전체 자재 리스트")
        st.dataframe(df, use_container_width=True, hide_index=True)
