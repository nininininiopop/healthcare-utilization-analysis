import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="고혈압·당뇨병 의료이용률 분석",
    page_icon="📊",
    layout="wide"
)

st.title("📊 고혈압·당뇨병 의료이용률 분석")
st.caption("국민건강보험공단 2024년 자료를 활용한 지역·연령·성별 데이터 분석")

DATA_FILE = "국민건강보험공단_고혈압 당뇨병 의료이용률_20241231 (1).CSV"

AGE_LABELS = {
    "00": "0~9세", "10": "10대", "20": "20대",
    "30": "30대", "40": "40대", "50": "50대",
    "60": "60대", "70": "70대", "80": "80세 이상"
}
AGE_ORDER = list(AGE_LABELS.keys())


@st.cache_data
def load_data():
    data = None
    for encoding in ["cp949", "utf-8-sig", "euc-kr", "utf-8"]:
        try:
            data = pd.read_csv(
                DATA_FILE,
                encoding=encoding,
                dtype={"성별": str, "연령그룹": str}
            )
            break
        except UnicodeDecodeError:
            continue

    if data is None:
        raise ValueError("CSV 파일의 인코딩을 읽을 수 없습니다.")

    required = [
        "기준연도", "시도", "시군구", "성별", "연령그룹",
        "분모(명)", "분자(명)", "고당의료이용률"
    ]
    missing = [column for column in required if column not in data.columns]
    if missing:
        raise ValueError("CSV에 필요한 열이 없습니다: " + ", ".join(missing))

    for column in ["기준연도", "분모(명)", "분자(명)", "고당의료이용률"]:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    data["성별"] = data["성별"].astype(str)
    data["연령그룹"] = data["연령그룹"].astype(str)
    return data.dropna(subset=["시도", "시군구", "고당의료이용률"])


try:
    df = load_data()
except Exception as error:
    st.error(f"데이터를 불러오지 못했습니다: {error}")
    st.info("main.py와 CSV 파일이 GitHub 저장소의 같은 폴더에 있는지 확인해 주세요.")
    st.stop()


# ==================================================
# 사이드바: 분석 조건
# ==================================================
st.sidebar.header("🔎 분석 조건")
st.sidebar.caption("조건을 바꾸면 요약 수치와 관련 그래프가 함께 바뀝니다.")

years = sorted(df["기준연도"].dropna().unique().tolist())
selected_year = st.sidebar.selectbox("기준연도", years, index=len(years) - 1)

region_options = sorted(
    df.loc[df["시도"] != "전국", "시도"].dropna().unique().tolist()
)
selected_region = st.sidebar.selectbox(
    "시도", ["전체"] + region_options
)

# 선택한 시도에 속한 시군구만 선택지에 표시
if selected_region == "전체":
    district_options = []
else:
    district_options = sorted(
        df.loc[
            (df["시도"] == selected_region) &
            (df["시군구"] != "전체"),
            "시군구"
        ].dropna().unique().tolist()
    )

selected_district = st.sidebar.selectbox(
    "시군구", ["전체"] + district_options,
    help="시도를 먼저 선택하면 해당 시도의 시군구를 고를 수 있습니다."
)

gender_options = {
    "전체": "ALL",
    "성별 코드 1": "1",
    "성별 코드 2": "2"
}
selected_gender_label = st.sidebar.selectbox(
    "성별", list(gender_options.keys())
)
selected_gender = gender_options[selected_gender_label]

age_options = {"전체 연령": "ALL"}
age_options.update({label: code for code, label in AGE_LABELS.items()})
selected_age_label = st.sidebar.selectbox(
    "연령대", list(age_options.keys())
)
selected_age = age_options[selected_age_label]

st.sidebar.divider()
st.sidebar.caption(
    "참고: 원본 CSV의 성별은 1·2·ALL 코드로 제공됩니다. "
    "코드표가 없어 남녀 명칭으로 임의 변환하지 않았습니다."
)


# ==================================================
# 공통 필터 함수
# ==================================================
year_df = df[df["기준연도"] == selected_year].copy()


def apply_common_filters(data, include_age=True, include_gender=True):
    result = data.copy()

    if selected_region != "전체":
        result = result[result["시도"] == selected_region]
    else:
        result = result[result["시도"] == "전국"]

    if selected_district != "전체":
        result = result[result["시군구"] == selected_district]
    else:
        result = result[result["시군구"] == "전체"]

    if include_gender:
        result = result[result["성별"] == selected_gender]

    if include_age:
        result = result[result["연령그룹"] == selected_age]

    return result


# 선택 조건에 맞는 KPI 행
summary = apply_common_filters(year_df)
rate = float(summary.iloc[0]["고당의료이용률"]) if not summary.empty else None
denominator = int(summary.iloc[0]["분모(명)"]) if not summary.empty else None
numerator = int(summary.iloc[0]["분자(명)"]) if not summary.empty else None

location_name = (
    f"{selected_region} {selected_district}"
    if selected_region != "전체" and selected_district != "전체"
    else selected_region
)
if selected_region != "전체" and selected_district == "전체":
    location_name = selected_region
elif selected_region == "전체":
    location_name = "전국"

st.subheader("선택 조건의 핵심 지표")
k1, k2, k3 = st.columns(3)
k1.metric(
    "고당 의료이용률",
    f"{rate:.2f}%" if rate is not None else "자료 없음"
)
k2.metric(
    "분모 인원",
    f"{denominator:,}명" if denominator is not None else "자료 없음"
)
k3.metric(
    "분자 인원",
    f"{numerator:,}명" if numerator is not None else "자료 없음"
)

st.caption(
    f"선택 조건: {selected_year}년 · {location_name} · "
    f"{selected_gender_label} · {selected_age_label}"
)
st.divider()


# ==================================================
# 분석 탭
# ==================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "① 지역별 비교",
    "② 연령·성별 분석",
    "③ 지역별 4단계 분류",
    "④ 상관관계 분석",
    "⑤ 데이터 확인"
])


# ① 지역별 비교
with tab1:
    st.subheader("지역별 고당 의료이용률 비교")

    if selected_region == "전체":
        comparison = year_df[
            (year_df["시도"] != "전국") &
            (year_df["시군구"] == "전체") &
            (year_df["성별"] == selected_gender) &
            (year_df["연령그룹"] == selected_age)
        ].copy()
        category_column = "시도"
        chart_title = "전국 시도별 의료이용률"
    elif selected_district == "전체":
        comparison = year_df[
            (year_df["시도"] == selected_region) &
            (year_df["시군구"] != "전체") &
            (year_df["성별"] == selected_gender) &
            (year_df["연령그룹"] == selected_age)
        ].copy()
        category_column = "시군구"
        chart_title = f"{selected_region} 시군구별 의료이용률"
    else:
        comparison = year_df[
            (year_df["시도"] == selected_region) &
            (year_df["시군구"] == selected_district) &
            (year_df["성별"] == selected_gender) &
            (year_df["연령그룹"] == selected_age)
        ].copy()
        category_column = "시군구"
        chart_title = f"{selected_region} {selected_district} 의료이용률"

    if comparison.empty:
        st.warning("선택한 조건에 해당하는 지역별 자료가 없습니다.")
    else:
        comparison = comparison.sort_values(
            "고당의료이용률", ascending=False
        )
        fig = px.bar(
            comparison,
            x="고당의료이용률",
            y=category_column,
            orientation="h",
            text="고당의료이용률",
            title=chart_title,
            labels={
                "고당의료이용률": "의료이용률(%)",
                category_column: "지역"
            }
        )
        fig.update_traces(
            texttemplate="%{text:.2f}%",
            textposition="outside"
        )
        fig.update_layout(
            yaxis={"categoryorder": "total ascending"},
            xaxis_title="의료이용률(%)",
            yaxis_title="",
            margin={"r": 65}
        )
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            comparison[
                ["시도", "시군구", "분모(명)", "분자(명)", "고당의료이용률"]
            ],
            use_container_width=True,
            hide_index=True
        )


# ② 연령·성별 분석
with tab2:
    st.subheader("연령대별 의료이용률 변화")
    st.caption(
        "연령 변화 그래프는 선택한 지역·시군구·성별 안에서 "
        "모든 연령대를 비교합니다."
    )

    if selected_region == "전체":
        age_source = year_df[
            (year_df["시도"] == "전국") &
            (year_df["시군구"] == "전체")
        ].copy()
    elif selected_district == "전체":
        age_source = year_df[
            (year_df["시도"] == selected_region) &
            (year_df["시군구"] == "전체")
        ].copy()
    else:
        age_source = year_df[
            (year_df["시도"] == selected_region) &
            (year_df["시군구"] == selected_district)
        ].copy()

    age_source = age_source[
        (age_source["성별"] == selected_gender) &
        (age_source["연령그룹"].isin(AGE_ORDER))
    ].copy()

    if age_source.empty:
        st.warning("연령대별 자료가 없습니다.")
    else:
        age_source["연령대"] = age_source["연령그룹"].map(AGE_LABELS)
        age_source["연령대"] = pd.Categorical(
            age_source["연령대"],
            categories=[AGE_LABELS[key] for key in AGE_ORDER],
            ordered=True
        )
        age_source = age_source.sort_values("연령대")
        fig_age = px.line(
            age_source,
            x="연령대",
            y="고당의료이용률",
            markers=True,
            text="고당의료이용률",
            title="연령대별 고당 의료이용률",
            labels={
                "연령대": "연령대",
                "고당의료이용률": "의료이용률(%)"
            }
        )
        fig_age.update_traces(
            texttemplate="%{text:.2f}%",
            textposition="top center"
        )
        st.plotly_chart(fig_age, use_container_width=True)

    st.divider()
    st.subheader("성별 코드별 의료이용률 비교")
    st.caption(
        "성별 비교 그래프는 선택한 지역에서 코드 1과 코드 2를 함께 보여줍니다."
    )

    gender_source = age_source.copy() if not age_source.empty else pd.DataFrame()
    if selected_region == "전체":
        gender_source = year_df[
            (year_df["시도"] == "전국") &
            (year_df["시군구"] == "전체")
        ].copy()
    elif selected_district == "전체":
        gender_source = year_df[
            (year_df["시도"] == selected_region) &
            (year_df["시군구"] == "전체")
        ].copy()
    else:
        gender_source = year_df[
            (year_df["시도"] == selected_region) &
            (year_df["시군구"] == selected_district)
        ].copy()

    gender_source = gender_source[
        (gender_source["성별"].isin(["1", "2"])) &
        (gender_source["연령그룹"].isin(AGE_ORDER))
    ].copy()

    if gender_source.empty:
        st.warning("성별 비교 자료가 없습니다.")
    else:
        gender_source["연령대"] = gender_source["연령그룹"].map(AGE_LABELS)
        gender_source["성별 코드"] = gender_source["성별"].map({
            "1": "성별 코드 1",
            "2": "성별 코드 2"
        })
        fig_gender = px.bar(
            gender_source,
            x="연령대",
            y="고당의료이용률",
            color="성별 코드",
            barmode="group",
            title="연령대별 성별 코드 비교",
            labels={
                "연령대": "연령대",
                "고당의료이용률": "의료이용률(%)"
            }
        )
        st.plotly_chart(fig_gender, use_container_width=True)


# ③ 지역별 4단계 분류
with tab3:
    st.subheader("시군구별 의료이용률 4단계 분류")
    st.write(
        "전국 시군구의 의료이용률 분포를 기준으로 하위 25%부터 "
        "상위 25%까지 네 그룹으로 나눕니다."
    )
    st.warning(
        "통계적 상대 분류이며 의학적 위험도나 공식 건강 등급을 의미하지 않습니다."
    )

    district_data = year_df[
        (year_df["시군구"] != "전체") &
        (year_df["시도"] != "전국") &
        (year_df["성별"] == selected_gender) &
        (year_df["연령그룹"] == selected_age)
    ].copy()

    # 분류 기준은 전국 시군구 전체로 계산하고, 화면은 선택 지역으로 좁힙니다.
    if district_data.empty:
        st.warning("선택한 성별·연령대의 시군구 자료가 없습니다.")
    else:
        district_data["백분위순위"] = district_data[
            "고당의료이용률"
        ].rank(method="first", pct=True)

        labels = [
            "1단계 낮음(하위 25%)",
            "2단계 중하(25~50%)",
            "3단계 중상(50~75%)",
            "4단계 높음(상위 25%)"
        ]
        district_data["분류"] = pd.cut(
            district_data["백분위순위"],
            bins=[0, 0.25, 0.50, 0.75, 1.0],
            labels=labels,
            include_lowest=True
        )

        q25, q50, q75 = district_data[
            "고당의료이용률"
        ].quantile([0.25, 0.50, 0.75]).tolist()

        st.markdown("**전국 시군구 기준 분류 경계값**")
        c1, c2, c3 = st.columns(3)
        c1.metric("하위 25% 경계", f"{q25:.2f}%")
        c2.metric("중앙값", f"{q50:.2f}%")
        c3.metric("상위 25% 경계", f"{q75:.2f}%")

        if selected_region != "전체":
            district_data = district_data[
                district_data["시도"] == selected_region
            ]
        if selected_district != "전체":
            district_data = district_data[
                district_data["시군구"] == selected_district
            ]

        counts = (
            district_data["분류"]
            .value_counts()
            .reindex(labels, fill_value=0)
            .rename_axis("분류")
            .reset_index(name="시군구 수")
        )
        fig_class = px.bar(
            counts,
            x="분류",
            y="시군구 수",
            color="분류",
            title="선택 지역의 의료이용률 단계별 분포",
            labels={"분류": "상대 분류", "시군구 수": "시군구 수"}
        )
        st.plotly_chart(fig_class, use_container_width=True)

        st.dataframe(
            district_data[
                ["시도", "시군구", "분모(명)", "분자(명)", "고당의료이용률", "분류"]
            ].sort_values("고당의료이용률", ascending=False),
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "분류 결과 CSV 다운로드",
            data=district_data.to_csv(index=False, encoding="utf-8-sig"),
            file_name="의료이용률_지역분류.csv",
            mime="text/csv"
        )


# ④ 상관관계 분석
with tab4:
    st.subheader("분모 인원과 의료이용률의 관계")
    st.caption(
        "선택한 시도·시군구·성별·연령대 조건에 맞는 시군구 자료를 표시합니다."
    )

    scatter_data = year_df[
        (year_df["시군구"] != "전체") &
        (year_df["시도"] != "전국") &
        (year_df["성별"] == selected_gender) &
        (year_df["연령그룹"] == selected_age)
    ].copy()

    if selected_region != "전체":
        scatter_data = scatter_data[
            scatter_data["시도"] == selected_region
        ]
    if selected_district != "전체":
        scatter_data = scatter_data[
            scatter_data["시군구"] == selected_district
        ]

    if scatter_data.empty:
        st.warning("선택 조건에 해당하는 자료가 없습니다.")
    else:
        fig_scatter = px.scatter(
            scatter_data,
            x="분모(명)",
            y="고당의료이용률",
            color="시도",
            hover_name="시군구",
            hover_data=["분자(명)"],
            title="시군구별 분모 인원과 의료이용률",
            labels={
                "분모(명)": "분모 인원(명)",
                "고당의료이용률": "의료이용률(%)"
            }
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

        if len(scatter_data) >= 2:
            corr = scatter_data[
                ["분모(명)", "고당의료이용률"]
            ].corr().iloc[0, 1]
            st.metric("상관계수", f"{corr:.3f}")
            st.caption(
                "상관계수는 두 변수의 관련성을 나타내며, "
                "상관관계만으로 원인과 결과를 판단할 수 없습니다."
            )
        else:
            st.info("상관계수는 비교 대상이 2개 이상일 때 계산할 수 있습니다.")


# ⑤ 데이터 확인
with tab5:
    st.subheader("선택 조건에 따른 원본 데이터")
    visible = year_df.copy()

    if selected_region != "전체":
        visible = visible[visible["시도"] == selected_region]
    else:
        visible = visible[visible["시도"] == "전국"]

    if selected_district != "전체":
        visible = visible[visible["시군구"] == selected_district]
    else:
        visible = visible[visible["시군구"] == "전체"]

    visible = visible[
        (visible["성별"] == selected_gender) &
        (visible["연령그룹"] == selected_age)
    ]

    st.write(f"조건에 해당하는 데이터: **{len(visible):,}행**")
    st.dataframe(visible, use_container_width=True, hide_index=True)

    st.download_button(
        "현재 조건의 데이터 CSV 다운로드",
        data=visible.to_csv(index=False, encoding="utf-8-sig"),
        file_name="선택조건_의료이용률_데이터.csv",
        mime="text/csv"
    )

st.divider()
st.caption(
    "자료: 국민건강보험공단 제공 CSV. 성별 코드 1·2의 의미는 "
    "원본 코드표 확인이 필요합니다. 의료이용률의 상대 분류는 "
    "공식 의학적 진단이나 위험도 판정이 아닙니다."
)
