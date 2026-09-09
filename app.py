import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import re
from datetime import date
import calendar

# ===== 설정 =====
st.set_page_config(page_title="NEIS 급식 분석", page_icon="🍱", layout="wide")

NEIS_API_KEY = "4700574c38d548efb942c1605da72a53"

# 미리 정의된 학교 목록 (검색 번거로움 해결)
SCHOOL_LIST = {
    "당곡고등학교": {"edu_code": "B10", "school_code": "7010582"},
    "서울고등학교": {"edu_code": "B10", "school_code": "7010146"},
    "경기고등학교": {"edu_code": "B10", "school_code": "7010358"},
    "숙명여자고등학교": {"edu_code": "B10", "school_code": "7010604"},
    "중앙고등학교": {"edu_code": "B10", "school_code": "7010179"},
}

MEAT_KEYWORDS = [
    "고기", "돈육", "돼지", "소고기", "쇠고기", "닭", "치킨", "육류",
    "불고기", "제육", "삼겹살", "갈비", "탕수육", "돈까스", "돈가스",
    "베이컨", "햄", "소시지", "미트볼", "육개장", "설렁탕", "곰탕",
    "삼계탕", "닭갈비", "닭볶음탕", "오리", "육회", "장조림",
    "떡갈비", "완자", "너비아니", "훈제", "스테이크", "가츠",
    "육전", "편육", "수육", "족발", "보쌈"
]


# ===== API 함수 =====
@st.cache_data(ttl=3600)
def get_meal_by_month(edu_code, school_code, year, month):
    """월간 급식 조회 (캐싱으로 속도 향상)"""
    start = f"{year}{month:02d}01"
    last_day = calendar.monthrange(year, month)[1]
    end = f"{year}{month:02d}{last_day}"

    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "KEY": NEIS_API_KEY,
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": edu_code,
        "SD_SCHUL_CODE": school_code,
        "MLSV_FROM_YMD": start,
        "MLSV_TO_YMD": end
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        rows = data["mealServiceDietInfo"][1]["row"]
        return [format_meal(r) for r in rows]
    except (KeyError, IndexError):
        return []
    except Exception as e:
        st.error(f"API 오류: {e}")
        return []


def format_meal(meal_info):
    menu_raw = meal_info["DDISH_NM"].replace("<br/>", "\n")
    menu_clean = re.sub(r'\([\d.]+\)', '', menu_raw).strip()
    menu_items = [m.strip() for m in menu_clean.split("\n") if m.strip()]

    cal_str = meal_info.get("CAL_INFO", "")
    cal_match = re.search(r'[\d.]+', cal_str)
    calorie = float(cal_match.group()) if cal_match else None

    return {
        "date": meal_info["MLSV_YMD"],
        "menu": menu_clean,
        "menu_items": menu_items,
        "calorie": calorie
    }


def contains_meat(menu_item):
    return any(kw in menu_item for kw in MEAT_KEYWORDS)


def analyze_vegan(meals):
    total = len(meals)
    if total == 0:
        return None
    meat_days = 0
    for m in meals:
        if any(contains_meat(item) for item in m["menu_items"]):
            meat_days += 1
    vegan_days = total - meat_days
    return {
        "total": total,
        "meat_days": meat_days,
        "meat_ratio": round(meat_days / total * 100, 1),
        "vegan_days": vegan_days,
        "vegan_ratio": round(vegan_days / total * 100, 1)
    }


# ===== 사이드바: 간단한 학교 선택 =====
st.sidebar.title("🏫 학교 선택")

selected_school_names = st.sidebar.multiselect(
    "학교를 선택하세요 (비교하려면 여러 개 선택)",
    options=list(SCHOOL_LIST.keys()),
    default=["당곡고등학교"]
)

if not selected_school_names:
    st.sidebar.warning("최소 1개 이상 선택해주세요.")
    st.stop()

selected_schools = [
    {"name": name, **SCHOOL_LIST[name]} for name in selected_school_names
]

col1, col2 = st.sidebar.columns(2)
year = col1.number_input("연도", min_value=2020, max_value=2030, value=date.today().year)
month = col2.number_input("월", min_value=1, max_value=12, value=date.today().month)

st.sidebar.markdown("---")
st.sidebar.caption("💡 목록에 없는 학교는 코드 하단 SCHOOL_LIST에 추가하면 됩니다.")


# ===== 메인 화면 =====
st.title("🍱 NEIS 급식 데이터 분석 앱")

tab1, tab2, tab3, tab4 = st.tabs(["📅 급식표", "📊 영양 대시보드", "🏫 학교 비교", "🌱 비건 분석"])

# ---------------- TAB 1: 급식표 ----------------
with tab1:
    st.header(f"{year}년 {month}월 급식표")

    school_name = st.selectbox("학교 선택", selected_school_names, key="tab1")
    school = next(s for s in selected_schools if s["name"] == school_name)

    meals = get_meal_by_month(school["edu_code"], school["school_code"], year, month)

    if meals:
        for m in meals:
            d = m["date"]
            formatted = f"{d[4:6]}월 {d[6:]}일"
            with st.expander(f"📆 {formatted}"):
                st.write(m["menu"])
                if m["calorie"]:
                    st.caption(f"칼로리: {m['calorie']} kcal")
    else:
        st.warning("⚠️ 급식 정보가 없습니다. 학교 코드가 정확한지 확인해주세요.")


# ---------------- TAB 2: 영양 대시보드 ----------------
with tab2:
    st.header("영양소 통계 (칼로리 추이)")

    school_name2 = st.selectbox("학교 선택", selected_school_names, key="tab2")
    school2 = next(s for s in selected_schools if s["name"] == school_name2)

    meals2 = get_meal_by_month(school2["edu_code"], school2["school_code"], year, month)

    if meals2:
        df = pd.DataFrame([
            {"날짜": f"{m['date'][4:6]}/{m['date'][6:]}", "칼로리": m["calorie"]}
            for m in meals2 if m["calorie"] is not None
        ])

        if not df.empty:
            fig = px.line(df, x="날짜", y="칼로리", markers=True,
                          title=f"{school_name2} 칼로리 추이")
            st.plotly_chart(fig, use_container_width=True)

            avg_cal = df["칼로리"].mean()
            st.metric("월평균 칼로리", f"{avg_cal:.0f} kcal")
        else:
            st.warning("칼로리 데이터가 없습니다.")
    else:
        st.warning("데이터가 없습니다.")


# ---------------- TAB 3: 학교 비교 ----------------
with tab3:
    st.header("학교별 칼로리 비교")

    if len(selected_schools) < 2:
        st.info("사이드바에서 2개 이상의 학교를 선택하면 비교할 수 있습니다.")
    else:
        compare_data = []
        for s in selected_schools:
            meals = get_meal_by_month(s["edu_code"], s["school_code"], year, month)
            for m in meals:
                if m["calorie"] is not None:
                    compare_data.append({
                        "학교": s["name"],
                        "날짜": f"{m['date'][4:6]}/{m['date'][6:]}",
                        "칼로리": m["calorie"]
                    })

        if compare_data:
            df_compare = pd.DataFrame(compare_data)

            fig = px.line(df_compare, x="날짜", y="칼로리", color="학교", markers=True,
                          title=f"{year}년 {month}월 학교별 칼로리 비교")
            st.plotly_chart(fig, use_container_width=True)

            avg_df = df_compare.groupby("학교")["칼로리"].mean().reset_index()
            fig2 = px.bar(avg_df, x="학교", y="칼로리", color="학교", text_auto=".0f",
                         title="학교별 평균 칼로리")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.warning("비교할 데이터가 없습니다.")


# ---------------- TAB 4: 비건 분석 ----------------
with tab4:
    st.header("🌱 비건 친화도 분석")
    st.caption("고기/육류 키워드 포함 여부로 분석합니다 (완벽하지 않을 수 있음)")

    vegan_results = []
    for s in selected_schools:
        meals = get_meal_by_month(s["edu_code"], s["school_code"], year, month)
        if meals:
            stats = analyze_vegan(meals)
            if stats:
                vegan_results.append({
                    "학교": s["name"],
                    "총 급식일": stats["total"],
                    "고기 포함일": stats["meat_days"],
                    "고기포함율(%)": stats["meat_ratio"],
                    "비건친화일": stats["vegan_days"],
                    "비건친화율(%)": stats["vegan_ratio"]
                })

    if vegan_results:
        df_vegan = pd.DataFrame(vegan_results).sort_values("비건친화율(%)", ascending=False)
        st.dataframe(df_vegan, use_container_width=True, hide_index=True)

        fig = px.bar(df_vegan, x="학교", y="비건친화율(%)", color="비건친화율(%)",
                     color_continuous_scale="Greens", text_auto=".1f",
                     title="학교별 비건 친화율")
        st.plotly_chart(fig, use_container_width=True)

        best = df_vegan.iloc[0]
        st.success(f"🥦 가장 비건 친화적인 학교: **{best['학교']}** ({best['비건친화율(%)']}%)")
    else:
        st.warning("분석할 데이터가 없습니다.")


st.markdown("---")
st.caption("데이터 출처: NEIS 교육정보 개방 포털")
