import streamlit as st
from supabase_client import supabase


def delete_uploaded_file_ui():
    st.subheader("🧹 업로드된 전표 삭제")

    # 1. 업로드된 파일 목록 불러오기
    uploaded_files = supabase.table("GeneralLedger") \
        .select("파일명") \
        .execute().data
    file_names = sorted({row["파일명"] for row in uploaded_files if row.get("파일명")})

    # 2. 사용자 선택 UI
    selected_file = st.selectbox("🗂️ 삭제할 파일을 선택하세요", ["선택 안함"] + file_names)

    # 3. 삭제 버튼
    if selected_file and selected_file != "선택 안함":
        if st.button("🗑️ 해당 파일 전표 삭제"):
            supabase.table("GeneralLedger") \
                .delete() \
                .eq("파일명", selected_file) \
                .execute()
            st.success(f"✅ '{selected_file}' 전표가 삭제되었습니다.")
            st.rerun()

    return file_names