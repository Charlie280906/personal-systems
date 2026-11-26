# IMPORTS
import streamlit as st


# DEFINE YOUR APPLICATION PAGES
pages = [
    st.Page("homePage.py", title="Home", icon=":material/home:"),
    st.Page("brainBoard.py", title="Brain Board", icon=":material/developer_board:"),
    st.Page("recipeBook.py", title="Recipe Book", icon=":material/kitchen:"),
    st.Page("cvBuilder.py", title="CV Builder", icon=":material/work_history:")
]


# --------------------------------
# 2. CONTROL NAVIGATION VISIBILITY
# --------------------------------

if st.user.is_logged_in:
    pg = st.navigation(pages, position="sidebar")
else:
    pg = st.navigation(pages, position="hidden")


# --------------------------------
# 3. AUTHENTICATION PAGE
# --------------------------------

if not st.user.is_logged_in:

    st.markdown(
        "<h1 style='text-align: center;'>Welcome to Personal Systems</h1>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<h4 style='text-align: center;'>Please log in to get started...</h4>",
        unsafe_allow_html=True,
    )

    st.write(" ")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.button(
            "Log in with Google",
            use_container_width=True,
            on_click=st.login
        )

    st.stop()


# --------------------------------
# 4. USER PROFILE
# --------------------------------


col1, col2 = st.sidebar.columns([1,4])
with col1:
    st.image(st.user.picture, width=60)
with col2:
    st.subheader(st.user.name)

st.sidebar.button(
    "Log out", use_container_width=True,
    on_click=st.logout, icon=":material/logout:"
)


# --------------------------------
# 5. RUN APPLICATION
# --------------------------------

pg.run()
