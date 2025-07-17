import streamlit as st
import pandas as pd
from supabase import create_client, Client
from supabase_client import supabase



def load_unmapped_options():
    inventory = supabase.table("Inventory").select("옵션ID, 등록상품명").execute().data
    inventory_df = pd.DataFrame(inventory)

    mapped = supabase.table("ItemMapping").select("옵션ID").execute().data
    mapped_ids = {item["옵션ID"] for item in mapped}

    return inventory_df[~inventory_df["옵션ID"].isin(mapped_ids)]

def show_mapping_ui():
    if "unmapped_df" not in st.session_state:
        st.session_state.unmapped_df = load_unmapped_options()

    unmapped_df = st.session_state.unmapped_df

    option_labels = [
        f"{row['옵션ID']} - {row['등록상품명']}" for _, row in unmapped_df.iterrows()
    ]
    option_values = unmapped_df["옵션ID"].tolist()
    label_to_id = dict(zip(option_labels, option_values))

    selected_labels = st.multiselect(
        "하나의 상품에 해당하는 옵션ID를 모두 선택하세요",
        options=option_labels
    )
    selected_option_ids = [label_to_id[label] for label in selected_labels]

    if selected_option_ids:
        st.write("선택된 옵션ID에 대해 마스터 정보 입력")

        first_id = selected_option_ids[0]
        default_name = unmapped_df[unmapped_df["옵션ID"] == first_id]["등록상품명"].values[0]

        masters = supabase.table("ItemMaster").select("마스터상품명").execute().data
        master_names = sorted({m["마스터상품명"] for m in masters if m.get("마스터상품명")})

        if "product_name" not in st.session_state:
            st.session_state["product_name"] = default_name
            st.session_state["manual_edit"] = False

        selected_existing_name = st.selectbox("기존 마스터상품명에서 선택", ["선택 안함"] + master_names)

        if selected_existing_name != "선택 안함":
            st.session_state["product_name"] = selected_existing_name
            st.session_state["manual_edit"] = False
        elif not st.session_state["manual_edit"]:
            st.session_state["product_name"] = default_name

        product_name = st.text_input("마스터상품명", value=st.session_state["product_name"])
        if product_name != st.session_state["product_name"]:
            st.session_state["product_name"] = product_name
            st.session_state["manual_edit"] = True

        existing_ids = supabase.table("ItemMaster").select("마스터ID").execute().data
        used_ids = {entry["마스터ID"] for entry in existing_ids if entry.get("마스터ID")}
        master_id = 1001 + len(used_ids)

        new_rows = [
            {"마스터ID": master_id, "마스터상품명": product_name, "옵션ID": oid}
            for oid in selected_option_ids
        ]

        st.markdown(f"""
        총 **{len(new_rows)}**개 옵션이  
        **마스터상품명 : {product_name}**  
        으/로 등록됩니다.
        """)

        if st.button("마스터ID 매핑 등록") and new_rows:
            for row in new_rows:
                supabase.table("ItemMaster").upsert({
                    "마스터ID": row["마스터ID"],
                    "마스터상품명": row["마스터상품명"]
                }).execute()

                supabase.table("ItemMapping").upsert({
                    "옵션ID": row["옵션ID"],
                    "마스터ID": row["마스터ID"]
                }).execute()

            st.success("마스터ID 및 옵션ID 매핑 등록 완료")
            st.session_state.unmapped_df = load_unmapped_options()
            st.rerun()
