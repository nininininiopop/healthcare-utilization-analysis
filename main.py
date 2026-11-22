import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="고혈압·당뇨병 의료이용률 분석",
    page_icon="📊",
    layout="wide"
)

st.title("📊 고혈압·당뇨병 의료이용률 분석")
st.caption("국민건강보험공단 · 2024년 기준 자료")

DATA_FILE = "국민건강보험공단_고혈압 당뇨병 의료이용률_20241231 (1).CSV"

@st.cache_data
def load_data():
    # 공공데이터 CSV는 한글 인코딩이 CP949인 경우가 있어 순서대로 시도합니다.
    for encoding in ("cp949", "utf-8-sig", "euc-kr", "utf-8"):
        try:
            data = pd.read_csv(DATA_FILE, encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("CSV 인코딩을 읽을 수 없습니다. CP949 또는 UTF-8 형식인지 확인해 주세요.")

    required = ["기준연도", "시도", "시군구", "성별", "연령그룹",
                "분모(명)", "분자(명)", "고당의료이용률"]
    missing = [col for col in required if col not in data.columns]
    if missing:
        raise ValueError(f"CSV에 필요한 열이 없습니다: {', '.join(missing)}")

    for col in ["분모(명)", "분자(명)", "고당의료이용률"]:
        data[col] = pd.to_numeric(data[col], errors="coerce")
    data["연령그룹"] = data["연령그룹"].astype(str)
    data["성별"] = data["성별"].astype(str)
    return data.dropna(subset=["시도", "시군구", "고당의료이용률"])

try:
    df = load_data()
except Exception as e:
    st.error(f"데이터를 불러오지 못했습니다: {e}")
    st.info("main.py와 CSV 파일을 같은 GitHub 저장소의 최상위 폴더에 올렸는지 확인해 주세요.")
    st.stop()

# 사이드바 필터
st.sidebar.header("분석 조건")
year_options = sorted(df["기준연도"].dropna().unique().tolist())
selected_year = st.sidebar.selectbox("기준연도", year_options, index=len(year_options)-1)

sido_options = sorted(df.loc[df["시도"] != "전국", "시도"].dropna().unique())
selected_sido = st.sidebar.selectbox("시도", ["전체"] + sido_options)

gender_options = sorted(df["성별"].dropna().unique())
selected_gender = st.sidebar.selectbox("성별", ["전체"] + gender_options)

base = df[df["기준연도"] == selected_year].copy()
if selected_sido != "전체":
    base = base[base["시도"] == selected_sido]
if selected_gender != "전체":
    base = base[base["성별"] == selected_gender]

# 연령별 분석에는 전체 연령(ALL) 행을 제외
age_order = ["00", "10", "20", "30", "40", "50", "60", "70", "80"]
age_labels = {
    "00": "0~9세", "10": "10대", "20": "20대", "30": "30대",
    "40": "40대", "50": "50대", "60": "60대", "70": "70대", "80": "80세 이상"
}
age_data = base[base["연령그룹"].isin(age_order)].copy()
age_data["연령대"] = age_data["연령그룹"].map(age_labels)

# 전체 행은 전국/시도·시군구 전체의 요약값을 나타내므로 지역별 비교에 사용
overall = base[(base["연령그룹"] == "ALL") & (base["시군구"] == "전체")].copy()

# 핵심 지표
c1, c2, c3 = st.columns(3)
if not overall.empty:
    c1.metric("의료이용률", f'{overall["고당의료이용률"].mean():.2f}%')
    c2.metric("분모 인원", f'{overall["분모(명)"].sum():,.0f}명')
    c3.metric("분자 인원", f'{overall["분자(명)"].sum():,.0f}명')
else:
    c1.metric("의료이용률", "-")
    c2.metric("분모 인원", "-")
    c3.metric("분자 인원", "-")

st.divider()

tab1, tab2, tab3 = st.tabs(["연령별 분석", "지역별 비교", "데이터 살펴보기"])

with tab1:
    st.subheader("연령대별 고당 의료이용률")
    if age_data.empty:
        st.warning("선택한 조건에 해당하는 연령별 데이터가 없습니다.")
    else:
        age_summary = (
            age_data.groupby("연령대", as_index=False)["고당의료이용률"]
            .mean()
        )
        age_summary["연령대"] = pd.Categorical(
            age_summary["연령대"],
            categories=[age_labels[x] for x in age_order],
            ordered=True
        )
        age_summary = age_summary.sort_values("연령대")
        fig = px.bar(
            age_summary, x="연령대", y="고당의료이용률",
            text_auto=".2f",
            labels={"연령대": "연령대", "고당의료이용률": "의료이용률(%)"},
            title="연령대별 의료이용률"
        )
        fig.update_layout(yaxis_title="의료이용률(%)", xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("연령대별 분모·분자 인원")
        count_summary = age_data.groupby("연령대", as_index=False)[["분모(명)", "분자(명)"]].sum()
        count_summary["연령대"] = pd.Categorical(
            count_summary["연령대"],
            categories=[age_labels[x] for x in age_order],
            ordered=True
        )
        count_summary = count_summary.sort_values("연령대")
        count_long = count_summary.melt(
            id_vars="연령대", value_vars=["분모(명)", "분자(명)"],
            var_name="구분", value_name="인원(명)"
        )
        fig2 = px.bar(
            count_long, x="연령대", y="인원(명)", color="구분", barmode="group",
            labels={"연령대": "연령대"},
            title="연령대별 분모·분자 인원"
        )
        st.plotly_chart(fig2, use_container_width=True)

with tab2:
    st.subheader("시도별 고당 의료이용률")
    region_base = df[
        (df["기준연도"] == selected_year) &
        (df["시군구"] == "전체") &
        (df["연령그룹"] == "ALL") &
        (df["성별"] == ("ALL" if selected_gender == "전체" else selected_gender)) &
        (df["시도"] != "전국")
    ].copy()

    if selected_sido != "전체":
        region_base = region_base[region_base["시도"] == selected_sido]

    if region_base.empty:
        st.warning("선택한 조건에 해당하는 지역별 요약 데이터가 없습니다.")
    else:
        region_base = region_base.sort_values("고당의료이용률", ascending=True)
        fig3 = px.bar(
            region_base, x="고당의료이용률", y="시도", orientation="h",
            text_auto=".2f",
            labels={"고당의료이용률": "의료이용률(%)", "시도": "시도"},
            title="시도별 의료이용률 비교"
        )
        st.plotly_chart(fig3, use_container_width=True)

    st.subheader("시군구별 의료이용률")
    if selected_sido == "전체":
        st.info("시군구를 비교하려면 왼쪽에서 특정 시도를 선택해 주세요.")
    else:
        district = df[
            (df["기준연도"] == selected_year) &
            (df["시도"] == selected_sido) &
            (df["시군구"] != "전체") &
            (df["연령그룹"] == "ALL") &
            (df["성별"] == ("ALL" if selected_gender == "전체" else selected_gender))
        ].copy()
        if district.empty:
            st.warning("해당 시도의 시군구 자료가 없습니다.")
        else:
            district = district.sort_values("고당의료이용률", ascending=False)
            fig4 = px.bar(
                district, x="시군구", y="고당의료이용률",
                labels={"시군구": "시군구", "고당의료이용률": "의료이용률(%)"},
                title=f"{selected_sido} 시군구별 의료이용률"
            )
            st.plotly_chart(fig4, use_container_width=True)

with tab3:
    st.subheader("원본 데이터")
    st.write(f"전체 {len(df):,}행 중 선택 조건에 해당하는 {len(base):,}행을 표시합니다.")
    st.dataframe(base, use_container_width=True, hide_index=True)
    csv_data = base.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        "현재 데이터 CSV 다운로드",
        data=csv_data,
        file_name="filtered_healthcare_data.csv",
        mime="text/csv"
    )

st.caption(
    "※ '고당의료이용률'은 원본 CSV에 제공된 지표를 그대로 사용합니다. "
    "성별 값(1, 2, ALL)은 원자료의 코드이며, 코드 의미는 별도 코드표 확인이 필요합니다."
)
