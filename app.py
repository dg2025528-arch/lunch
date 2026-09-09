import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from dotenv import load_dotenv
from datetime import datetime, date

from neis_api import NeisMealAPI, SchoolSearch
from vegan_analyzer import VeganAnalyzer

# ===== 환경 설정 =====
load_dotenv()
NEIS_API_KEY = os.getenv("NEIS_API_KEY", "4700574c38d548efb942c1605da72a53")

st.set_page_config(page_title="NEIS 급식 분석", page_icon="🍱", layout="wide")

meal_api = NeisMealAPI(NEIS_API_KEY)
school_search = SchoolSearch(NEIS_API_KEY)
vegan_analyzer = VeganAnalyzer()

# ===== 세션 상태 초기화 =====
DEFAULT_SCHOOL = {
    "name": "당곡고등학교",
    "edu_code": "B10",       # 서울특별시교육청
    "school_code": "7530623" # 당곡고등학교 표준학교코드 (확인 필요)
}

if "selected_schools" not in st.session_state:
    st.session_state.selected_schools = [DEFAULT_SCHOOL]

# ===== 사이드바: 학교 검색 & 선택 =====
st.sidebar.title("🏫 학교 선택")
st.sidebar.caption("최소 3개 이상의 학교를 선택하면 비교가 가능합니다.")

search_query = st.sidebar.text_input("학교 이름 검색", placeholder="예: 당곡고등학교")

if search_query:
    with st.spinner("검색 중..."):
        results = school_search.search_school(search_query)
    if results:
        options = {f"{s['name']} ({s['address']})": s for s in results}
        picked = st.sidebar.selectbox("검색 결과에서 선택", list(options.keys()))
        if st.sidebar.button("➕ 학교 추가"):
            school_to_add = options[picked]
            existing_codes = [s["school_code"] for s in st.session_state.selected_schools]
            if school_to_add["school_code"] not in existing_codes:
                st.session_state.selected_schools.append(school_to_add)
                st.sidebar.success(f"{school_to_add['name']} 추가됨")
            else:
                st.sidebar.warning("이미 추가된 학교입니다.")
    else:
        st.sidebar.warning("검색 결과가 없습니다.")

st.sidebar.markdown("---")
st.sidebar.subheader("선택된 학교 목록")
for idx, s in enumerate(st.session_state.selected_schools):
    col1, col2 = st.sidebar.columns([4, 1])
    col1.write(f"{idx+1}. {s['name']}")
    if len(st.session_state.selected_schools) > 1:
        if col2.button("❌", key=f"remove_{idx}"):
            st.session_state.selected_schools.pop(idx)
            st.rerun()

if len(st.session_state.selected_schools) < 3:
    st.sidebar.info(f"⚠️ 비교를 위해 {3 - len(st.session_state.selected_schools)}개 학교를 더 추가해주세요.")

# ===== 메인 화면 =====
st.title("🍱 NEIS 급식 데이터 분석 앱")

tab1, tab2, tab3, tab4 = st.tabs(["📅 급식표 조회", "📊 영양소 대시보드", "🏫 학교 비교", "🌱 비건 친화도 분석"])

schools = st.session_state.selected_schools

# ---------------------------------------------------------
# TAB 1: 주간/월간 급식표
# ---------------------------------------------------------
with tab1:
    st.header("급식표 조회")
    
    target_school_name = st.selectbox(
        "학교 선택",
        [s["name"] for s in schools],
        key="tab1_school"
    )
    target_school = next(s for s in schools if s["name"] == target_school_name)
    
    view_type = st.radio("조회 방식", ["주간", "월간"], horizontal=True)
    
    if view_type == "주간":
        selected_date = st.date_input("조회 시작일", value=date.today())
        start_str = selected_date.strftime("%Y%m%d")
        
        with st.spinner("급식 정보를 불러오는 중..."):
            meals = meal_api.get_meal_by_week(
                target_school["edu_code"], target_school["school_code"], start_str
            )
        
        if meals:
            for meal in meals:
                d = meal["date"]
                formatted_date = f"{d[:4]}-{d[4:6]}-{d[6:]}"
                with st.expander(f"📆 {formatted_date}", expanded=True):
                    st.write(meal["menu"])
                    st.caption(f"칼로리: {meal['calorie']}")
        else:
            st.warning("해당 기간의 급식 정보가 없습니다.")
    
    else:  # 월간
        col1, col2 = st.columns(2)
        year = col1.number_input("연도", min_value=2020, max_value=2030, value=date.today().year)
        month = col2.number_input("월", min_value=1, max_value=12, value=date.today().month)
        
        with st.spinner("급식 정보를 불러오는 중..."):
            meals = meal_api.get_meal_by_month(
                target_school["edu_code"], target_school["school_code"], year, month
            )
        
        if meals:
            df = pd.DataFrame([
                {"날짜": f"{m['date'][:4]}-{m['date'][4:6]}-{m['date'][6:]}", "메뉴": m["menu"].replace("\n", ", ")}
                for m in meals
            ])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.warning("해당 월의 급식 정보가 없습니다.")

# ---------------------------------------------------------
# TAB 2: 영양소 통계 대시보드 (Plotly)
# ---------------------------------------------------------
with tab2:
    st.header("영양소 통계 대시보드")
    
    target_school_name2 = st.selectbox(
        "학교 선택",
        [s["name"] for s in schools],
        key="tab2_school"
    )
    target_school2 = next(s for s in schools if s["name"] == target_school_name2)
    
    col1, col2 = st.columns(2)
    year2 = col1.number_input("연도", min_value=2020, max_value=2030, value=date.today().year, key="y2")
    month2 = col2.number_input("월", min_value=1, max_value=12, value=date.today().month, key="m2")
    
    with st.spinner("영양 정보를 분석하는 중..."):
        meals2 = meal_api.get_meal_by_month(
            target_school2["edu_code"], target_school2["school_code"], year2, month2
        )
    
    if meals2:
        nutrition_records = []
        for m in meals2:
            record = {"날짜": f"{m['date'][4:6]}/{m['date'][6:]}"}
            # 칼로리 파싱
            try:
                cal = float(m["calorie"].replace("Kcal", "").strip())
                record["칼로리"] = cal
            except (ValueError, AttributeError):
                record["칼로리"] = None
            record.update(m["nutrition"])
            nutrition_records.append(record)
        
        df_nutrition = pd.DataFrame(nutrition_records)
        
        # 칼로리 추이 그래프
        if "칼로리" in df_nutrition.columns:
            fig_cal = px.line(
                df_nutrition, x="날짜", y="칼로리",
                title=f"{target_school2['name']} - {year2}년 {month2}월 일별 칼로리 추이",
                markers=True
            )
            fig_cal.update_layout(yaxis_title="칼로리 (Kcal)")
            st.plotly_chart(fig_cal, use_container_width=True)
        
        # 영양소별 평균 (레이더 차트)
        nutrient_cols = [c for c in df_nutrition.columns if c not in ["날짜", "칼로리"]]
        if nutrient_cols:
            avg_values = df_nutrition[nutrient_cols].mean()
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=avg_values.values,
                theta=avg_values.index,
                fill='toself',
                name='평균 영양소'
            ))
            fig_radar.update_layout(
                title="영양소별 월평균 (레이더 차트)",
                polar=dict(radialaxis=dict(visible=True))
            )
            st.plotly_chart(fig_radar, use_container_width=True)
        
        with st.expander("원본 데이터 보기"):
            st.dataframe(df_nutrition, use_container_width=True)
    else:
        st.warning("해당 월의 데이터가 없습니다.")

# ---------------------------------------------------------
# TAB 3: 학교 비교 (3개 이상)
# ---------------------------------------------------------
with tab3:
    st.header("학교별 칼로리 비교")
    
    if len(schools) < 3:
        st.error("최소 3개 이상의 학교를 사이드바에서 추가해주세요!")
    else:
        col1, col2 = st.columns(2)
        year3 = col1.number_input("연도", min_value=2020, max_value=2030, value=date.today().year, key="y3")
        month3 = col2.number_input("월", min_value=1, max_value=12, value=date.today().month, key="m3")
        
        compare_data = []
        with st.spinner("여러 학교 데이터를 불러오는 중..."):
            for s in schools:
                meals = meal_api.get_meal_by_month(s["edu_code"], s["school_code"], year3, month3)
                for m in meals:
                    try:
                        cal = float(m["calorie"].replace("Kcal", "").strip())
                    except (ValueError, AttributeError):
                        cal = None
                    compare_data.append({
                        "학교": s["name"],
                        "날짜": f"{m['date'][4:6]}/{m['date'][6:]}",
                        "칼로리": cal
                    })
        
        if compare_data:
            df_compare = pd.DataFrame(compare_data)
            
            # 선 그래프로 학교별 비교
            fig_compare = px.line(
                df_compare, x="날짜", y="칼로리", color="학교",
                title=f"{year3}년 {month3}월 학교별 칼로리 비교",
                markers=True
            )
            st.plotly_chart(fig_compare, use_container_width=True)
            
            # 학교별 평균 칼로리 막대 그래프
            avg_by_school = df_compare.groupby("학교")["칼로리"].mean().reset_index()
            fig_bar = px.bar(
                avg_by_school, x="학교", y="칼로리",
                title="학교별 평균 칼로리",
                color="학교", text_auto=".1f"
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.warning("비교할 데이터가 없습니다.")

# ---------------------------------------------------------
# TAB 4: 비건 친화도 분석
# ---------------------------------------------------------
with tab4:
    st.header("🌱 비건 친화 학교 분석")
    st.caption("고기/육류/해산물 키워드가 급식 메뉴에 포함되는 빈도를 분석합니다.")
    
    if len(schools) < 3:
        st.warning("최소 3개 이상의 학교를 추가하면 순위 비교가 가능합니다. (1개 학교 분석은 아래에서 가능)")
    
    col1, col2 = st.columns(2)
    year4 = col1.number_input("연도", min_value=2020, max_value=2030, value=date.today().year, key="y4")
    month4 = col2.number_input("월", min_value=1, max_value=12, value=date.today().month, key="m4")
    
    vegan_results = []
    with st.spinner("비건 친화도를 분석하는 중..."):
        for s in schools:
            meals = meal_api.get_meal_by_month(s["edu_code"], s["school_code"], year4, month4)
            if meals:
                stats = vegan_analyzer.analyze_period(meals)
                if stats:
                    vegan_results.append({
                        "학교": s["name"],
                        "총 급식일수": stats["total_days"],
                        "고기 포함일": stats["meat_days"],
                        "고기 포함율(%)": stats["meat_ratio"],
                        "비건친화일": stats["vegan_friendly_days"],
                        "비건친화율(%)": stats["vegan_ratio"]
                    })
    
    if vegan_results:
        df_vegan = pd.DataFrame(vegan_results).sort_values("비건친화율(%)", ascending=False)
        
        st.subheader("🏆 비건 친화도 순위 (높을수록 비건 식단 친화적)")
        st.dataframe(df_vegan, use_container_width=True, hide_index=True)
        
        # 비건 친화율 막대 그래프
        fig_vegan = px.bar(
            df_vegan, x="학교", y="비건친화율(%)",
            title="학교별 비건 친화율",
            color="비건친화율(%)",
            color_continuous_scale="Greens",
            text_auto=".1f"
        )
        st.plotly_chart(fig_vegan, use_container_width=True)
        
        # 고기 포함율 vs 비건친화율 비교 (스택 막대)
        fig_stack = go.Figure()
        fig_stack.add_trace(go.Bar(
            name='고기 포함율', x=df_vegan["학교"], y=df_vegan["고기 포함율(%)"],
            marker_color='indianred'
        ))
        fig_stack.add_trace(go.Bar(
            name='비건친화율', x=df_vegan["학교"], y=df_vegan["비건친화율(%)"],
            marker_color='seagreen'
        ))
        fig_stack.update_layout(barmode='group', title="학교별 고기 포함 vs 비건친화 비율")
        st.plotly_chart(fig_stack, use_container_width=True)
        
        # 가장 비건 친화적인 학교 하이라이트
        best_school = df_vegan.iloc[0]
        st.success(f"🥦 이번 달 가장 비건 친화적인 학교: **{best_school['학교']}** (비건친화율 {best_school['비건친화율(%)']}%)")
        
        with st.expander("상세 데이터 (일별 고기 메뉴 확인)"):
            for s in schools:
                meals = meal_api.get_meal_by_month(s["edu_code"], s["school_code"], year4, month4)
                if meals:
                    stats = vegan_analyzer.analyze_period(meals)
                    st.write(f"**{s['name']}**")
                    for d in stats["daily_results"]:
                        if d["meat_count"] > 0:
                            st.write(f"- {d['date']}: 🥩 {', '.join(d['meat_items'])}")
                    st.markdown("---")
    else:
        st.warning("분석할 데이터가 없습니다.")

# ===== 푸터 =====
st.markdown("---")
st.caption("데이터 출처: NEIS 교육정보 개방 포털 (open.neis.go.kr)")
