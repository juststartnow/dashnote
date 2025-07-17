
import streamlit as st
from supabase import create_client, Client
from supabase_client import supabase
import pandas as pd
from JWT import show_metabase_dashboard


def show():

    # supabase 데이터 로드
    @st.cache_data
    def load_tables():
        ledger = supabase.table("GeneralLedger").select("*").execute().data
        mapping = supabase.table("ItemMapping").select("*").execute().data
        master = supabase.table("ItemMaster").select("*").execute().data
        account = supabase.table("Accounts").select("*").execute().data

        return (
            pd.DataFrame(ledger),
            pd.DataFrame(mapping),
            pd.DataFrame(master),
            pd.DataFrame(account),
        )

    ledger_df, mapping_df, master_df, account_df = load_tables()


    # 최종 가공 데이터 프레임 생성
    ledger_with_master = ledger_df.merge(
        mapping_df[["옵션ID", "마스터ID"]],
        on="옵션ID",
        how="left"
    )

    ledger_with_master = ledger_with_master.merge(
        master_df[["마스터ID", "마스터상품명"]],
        on="마스터ID",
        how="left"
    )

    ledger_with_master = ledger_with_master.merge(
        account_df[["계정코드", "계정과목명"]],
        on="계정코드",
        how="left"
    )
    col1, col2 = st.columns([2, 1]) 

    with col2:
        # 기준 필터 UI
        available_masters = ledger_with_master["마스터ID"].dropna().unique().tolist()
        selected_master = st.selectbox("📌 마스터ID 선택", sorted(available_masters))

        months = ledger_df["일자"].dropna().astype(str).str[:7].unique()
        selected_month = st.selectbox("📆 월 선택", sorted(months))



    with col1:
        # 선택 필터로 자료 재구성
        filtered_df = ledger_with_master.copy()

        if selected_master:
            filtered_df = filtered_df[filtered_df["마스터ID"] == selected_master]

        if selected_month:
            filtered_df = filtered_df[filtered_df["일자"].str.startswith(selected_month)]

        # 수익, 비용 분리
        sales_df = filtered_df[filtered_df["계정코드"].astype(str).str.startswith("4")]
        costs_df = filtered_df[filtered_df["계정코드"].astype(str).str.startswith("5")]

        # 금액 합산
        sales_total = sales_df["금액"].sum()
        costs_total = costs_df["금액"].sum()
        profit = sales_total - costs_total

        # 결과 표시
        st.metric("총 매출", f"{sales_total:,.0f} 원")
        st.metric("총 비용", f"{costs_total:,.0f} 원")
        st.metric("총 이익", f"{profit:,.0f} 원")

