import streamlit as st
from supabase_client import supabase

st.set_page_config(page_title="쿠팡 손익분석기", layout="wide")

# 세션 상태 초기화
if "user" not in st.session_state:
    st.session_state.user = None
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "login"  # 또는 "signup"

# 로그인 or 회원가입 탭
auth_tab = st.radio("인증 방식 선택", ["🔐 로그인", "📝 회원가입"], index=0)
st.session_state.auth_mode = "login" if auth_tab == "🔐 로그인" else "signup"

email = st.text_input("이메일")
password = st.text_input("비밀번호", type="password")

if st.session_state.auth_mode == "signup":
    confirm = st.text_input("비밀번호 확인", type="password")
    if st.button("회원가입"):
        if password != confirm:
            st.error("❌ 비밀번호가 일치하지 않습니다.")
        else:
            try:
                result = supabase.auth.sign_up({
                    "email": email,
                    "password": password
                })
                st.success("✅ 회원가입 성공! 이메일 인증 후 로그인하세요.")
            except Exception as e:
                st.error(f"❌ 회원가입 실패: {e}")

elif st.session_state.auth_mode == "login":
    if st.button("로그인"):
        try:
            result = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            st.session_state.user = result.user
            st.success("✅ 로그인 성공!")
            st.experimental_rerun()
        except Exception as e:
            st.error(f"❌ 로그인 실패: {e}")

# 로그인된 경우만 메인화면으로 이동
if st.session_state.user:
    st.success(f"환영합니다, {st.session_state.user.email}님!")

    # 메뉴 표시
    menu = st.sidebar.radio("📂 메뉴 선택", ["📥 데이터 입력", "📊 데이터 출력"])

    import input_view
    import output_view

    if menu == "📥 데이터 입력":
        input_view.show()

    elif menu == "📊 데이터 출력":
        output_view.show()

    if st.sidebar.button("🔓 로그아웃"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.experimental_rerun()
