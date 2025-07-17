import streamlit as st
import pandas as pd
from supabase_client import supabase
from journal_router import JournalRouter
from supabase import create_client, Client
from inventory import InventoryGenerator
from masterid_mapping import show_mapping_ui
from file_delete import delete_uploaded_file_ui

def show():
    st.markdown("업로드된 쿠팡 엑셀 데이터를 바탕으로 옵션ID별 매출과 비용을 분석합니다.")

    # 삭제 UI (업로드된 파일명 목록 반환)
    file_names = delete_uploaded_file_ui()

    # 마스터 매핑 UI
    show_mapping_ui()

    # 인벤토리 업로드
    uploaded_file = st.file_uploader("Inventory 엑셀 파일을 업로드하세요", type=["xlsx", "xls"])
    if uploaded_file:
        inventory = InventoryGenerator()
        inventory_df = inventory.generate(uploaded_file)
        st.dataframe(inventory_df.head())

        if st.button("업로드 실행", key="inventory_upload_button"):
            records = inventory_df.to_dict(orient="records")
            supabase.table("Inventory").upsert(records).execute()
            st.success("Inventory 업로드 완료!")

    # 정산 파일 업로드
    uploaded_files = st.file_uploader(
        "8개 정산 파일을 모두 업로드하세요", 
        type=["xlsx"], 
        accept_multiple_files=True,
        key="uploader"
    )

    combined_df = pd.DataFrame()

    if uploaded_files:
        all_entries = []

        for file in uploaded_files:
            filename = file.name

            if filename in file_names:
                st.warning(f"🚫 '{filename}' 은 이미 업로드된 파일입니다.")
                continue

            st.markdown(f"📁 {filename}")
            router = JournalRouter()
            journal_entries_df = router.route(file, filename)

            if journal_entries_df is not None and not journal_entries_df.empty:
                all_entries.append(journal_entries_df)

        if all_entries:
            combined_df = pd.concat(all_entries, ignore_index=True)
            st.dataframe(combined_df)
        else:
            st.warning("전표 데이터가 유효하지 않거나 비어있습니다.")

    # 업로드 실행 버튼
    if st.button("업로드 실행", key="upload_journal_button"):
        if not combined_df.empty:
            combined_df.replace({"": None}, inplace=True)
            records = combined_df.to_dict(orient="records")
            supabase.table("GeneralLedger").insert(records).execute()
            st.success("GeneralLedger 업로드 완료!")
        else:
            st.error("결합된 전표 데이터가 없습니다. 파일을 먼저 업로드해주세요.")