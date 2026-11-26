# TODO: get this on a git repo and have -v control working

# IMPORTS
import streamlit as st
from pathlib import Path
import json

# PAGE SETUP
st.set_page_config(
    page_title="Brain Board",
    layout="wide"
)

# LOADING THE BOARD DATA JSON FILE
board_data_file_path = Path("../brainBoardData") / "brainBoardStorage.json"
with open(board_data_file_path, 'r') as board_data_file:
    board_data = json.load(board_data_file)


def createDatesContainer():
    with st.container(border=True, height="content", gap="xxsmall"):
        st.markdown(
            "<h1 style=''>Dates</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<h8 style='text-align: center; color: gray;'>People</h1>",
            unsafe_allow_html=True,
        )
        with st.container(horizontal=True):
            st.write("Charlie's Birthday")
            with st.container():
                st.write("Thu 12th Nov")



createDatesContainer()

def createMealContainer():
    with st.container(border=True, width="content", height="content"):
        st.title("Meals")
        st.subheader("Health")

        st.markdown(
            "<h1 style=''>Meals</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<h8 style='text-align: center; color: gray;'>Health</h1>",
            unsafe_allow_html=True,
        )

        st.markdown(
            "<h8 style='font-family: cascadia-code;'>Health</h1>",
            unsafe_allow_html=True,
        )

        day_list = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        for count in range (0,7):
            with st.container(horizontal=True, horizontal_alignment="center", vertical_alignment="center"):
                st.write(day_list[count])
                st.checkbox("", key=day_list[count]+"-meal-check")
                st.text_input("", key=day_list[count]+"-meal-text", label_visibility="collapsed")


        # col1, col2, col3 = st.columns(3)
        # day_list = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        # with col1:
        #     with st.container():
        #         for count in range (0,7):
        #             st.write(day_list[count])
        # with col2:
        #     with st.container():
        #         for count in range (0,7):
        #             st.checkbox("", key=day_list[count]+"-meal-check")
        # with col3:
        #     with st.container():
        #         for count in range(0, 7):
        #             with st.container():
        #                 st.text_input("", key=day_list[count] + "-meal-text", label_visibility="collapsed")


st.write(board_data)


st.title("Life ... on a board 🤔")


container_categories = list(board_data["categories"])

with st.container(horizontal=True, vertical_alignment="center", horizontal_alignment="distribute"):
    st.pills("", container_categories, label_visibility="collapsed")

    with st.popover("Add to board", type="primary", icon=":material/add:", width="content"):


        @st.dialog("Add to dates")
        def date_adder():
            date_title = st.text_input("Date title...")
            date_value = st.date_input("Date occurs on...", format="DD-MM-YYYY")
            if st.button("Save", icon="💾"):
                board_data["dates"].append([date_title, date_value]) # TODO; fix why this line isn't actually appending to the list
                st.rerun()
        if "date_adder" not in st.session_state:
            if st.button("Important date", type="tertiary", icon="📅"):
                date_adder()

st.write(board_data["dates"])

# FIX:

st.divider()

createMealContainer()