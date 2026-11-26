# IMPORTS
import streamlit as st
import json
from pathlib import Path
import os
import sys


# appPageFiles/ -> personalSystems/ -> cvBuilderData/
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(HERE), "cvBuilderData")
CV_TEMPLATE = os.path.join(DATA_DIR, "cvTemplate.json")

# make fullRewrite.py importable
sys.path.insert(0, DATA_DIR)
import fullRewrite

CREDENTIALS = os.path.join(DATA_DIR, "credentials.json")
TOKEN = os.path.join(DATA_DIR, "token.json")
CV_JSON = os.path.join(DATA_DIR, "cvInfo.json")


def update_cv(doc_link, json_file=CV_JSON, sort_certs=True):
    with open(json_file, encoding="utf-8") as f:
        data = json.load(f)

    service = fullRewrite.get_service(CREDENTIALS, TOKEN)
    doc_id = fullRewrite.parse_doc_id(doc_link)
    fullRewrite.build_doc(service, doc_id, data, sort_certs=sort_certs)
    return f"https://docs.google.com/document/d/{doc_id}/edit"

def rewriteToJson():
    with open(cv_data_file_path_template, "w") as cv_template_file:
        json.dump(cv_template_data, cv_template_file, indent=4)
    with open(cv_data_file_path_info, "w") as cv_info_file:
        json.dump(cv_info_data, cv_info_file, indent=4)


@st.dialog("Add new item")
def createNew(type):
    if type == "qualification":
        qualification_title = st.text_input("Qualification name")
        qualification_date = st.text_input("When did you complete this")
        if st.button("Add", icon="➕", type="primary"):
            cv_info_data["certificates/qualifications"]["options"].append([qualification_title, qualification_date])
            rewriteToJson()
            st.rerun()
    
    if type == "employment":
        employment_place = st.text_input("Employer name")
        employment_date = st.text_input("Date range")
        employment_role = st.text_input("Role")
        employment_description = st.text_input("Description")
        if st.button("Add", icon="➕", type="primary"):
            cv_info_data["employment"][employment_place] = {"dates" : employment_date, "role" : employment_role, "description" : employment_description}
            rewriteToJson()
            st.rerun()

    if type == "volunteering":
        volunteering_place = st.text_input("Place")
        volunteering_date = st.text_input("Date range")
        volunteering_role = st.text_input("Role")
        volunteering_description = st.text_input("Description")
        if st.button("Add", icon="➕", type="primary"):
            cv_info_data["work experience/volunteering"][volunteering_place] = {"dates" : volunteering_date, "role" : volunteering_role, "description" : volunteering_description}
            rewriteToJson()
            st.rerun()

def saveData():
    if st.session_state.my_tabs == headings[0]:
        cv_template_data["personal details"]["name"] = name
        cv_template_data["personal details"]["location"] = location
        if location not in cv_info_data["personal details"]["location"]:
            cv_info_data["personal details"]["location"].append(location)
        cv_template_data["personal details"]["phone"] = phone
        if phone not in cv_info_data["personal details"]["phone"]:
            cv_info_data["personal details"]["phone"].append(phone)
        cv_template_data["personal details"]["email"] = email
        cv_template_data["personal details"]["driving licenses"] = driving_license

    if st.session_state.my_tabs == headings[1]:
        cv_template_data["introduction"] = main_introduction
        cv_info_data["introduction"] = main_introduction

    if st.session_state.my_tabs == headings[2]:
        if education_checkbox_states["a-levels"] == True and education_checkbox_states["gcses"] == True:
            cv_template_data["education"] = cv_info_data["education"]
        elif education_checkbox_states["a-levels"] == True:
            cv_template_data["education"] = cv_info_data["education"]["a-levels"]
        elif education_checkbox_states["gcses"] == True:
            cv_template_data["education"] = cv_info_data["education"]["gcses"]

    if st.session_state.my_tabs == headings[3]:
        cv_template_data["certificates/qualifications"]["intro"] = qualification_introduction
        cv_info_data["certificates/qualifications"]["intro"] = qualification_introduction
        temp_hold = []
        for qualification_item in qualification_checkbox_states:
            if qualification_checkbox_states[qualification_item] == True:
                for nested_section in cv_info_data["certificates/qualifications"]["options"]:
                    if nested_section[0] == qualification_item:
                        temp_hold.append(nested_section)
        cv_template_data["certificates/qualifications"]["options"] = temp_hold

    if st.session_state.my_tabs == headings[4]:
        cv_template_data["employment"] = {}
        for employment_item in employment_checkbox_states:
            if employment_checkbox_states[employment_item] == True:
                cv_template_data["employment"][employment_item] = cv_info_data["employment"][employment_item]

    if st.session_state.my_tabs == headings[5]:
        cv_template_data["work experience/volunteering"] = {}
        for we_v_item in we_v_checkbox_states:
            if we_v_checkbox_states[we_v_item] == True:
                cv_template_data["work experience/volunteering"][we_v_item] = cv_info_data["work experience/volunteering"][we_v_item]

    if st.session_state.my_tabs == headings[7]:
        cv_template_data["skills"] = skills
        for skill in skills:
            if skill not in cv_info_data["skills"]:
                cv_info_data["skills"].append(skill)

    if st.session_state.my_tabs == headings[8]:
        cv_template_data["interests/hobbies"] = free_time
        for hobby in free_time:
            if hobby not in cv_info_data["interests/hobbies"]:
                cv_info_data["interests/hobbies"].append(hobby)

    rewriteToJson()

    st.toast("Your changes were saved!", icon="✅")

# PAGE SETUP
st.set_page_config(
    page_title="My CV Builder",
    layout="wide"
)
st.title("My CV Builder")




# LOADING THE TEMPLATE SO WE CAN STORE INFO AS WE GO
cv_data_file_path_template = Path("../cvBuilderData") / "cvTemplate.json"
with open(cv_data_file_path_template, 'r') as cv_template_file:
    cv_template_data = json.load(cv_template_file)


# LOADING IN DATA FROM CVINFO.JSON
cv_data_file_path_info = Path("../cvBuilderData") / "cvInfo.json"
with open(cv_data_file_path_info, 'r') as cv_info_file:
    cv_info_data = json.load(cv_info_file)


# CREATING THE TAB HEADINGS FOR EACH CV SECTION
headings = []
counter = 1

for header in list(cv_info_data.keys()):
    headings.append(str(counter) + ". " + header.title())
    counter += 1

headings.append(str(counter) + ". Finalise")

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs(headings, key="my_tabs", on_change="rerun")


# PERSONAL INFORMATION TAB
with tab1:
    name = st.text_input("Name", cv_info_data["personal details"]["name"])
    location = st.selectbox("Location", cv_info_data["personal details"]["location"], accept_new_options=True)
    phone = st.selectbox("Phone number", cv_info_data["personal details"]["phone"], accept_new_options=True)
    email = st.text_input("Email", cv_info_data["personal details"]["email"])
    driving_license = st.multiselect("Driving Licenses", cv_info_data["personal details"]["driving licenses"])
    save_button = st.button("Save this section", icon="💾", on_click=saveData, use_container_width=True, key="save_personal_information")


# MAIN CV INTRODUCTION TAB
with tab2:
    main_introduction = st.text_area("This is the section that will sit under your name at the start of the CV...", cv_info_data["introduction"], height="content")
    save_button = st.button("Save this section", icon="💾", on_click=saveData, use_container_width=True, key="save_introduction")


# EDUCATION TAB
with tab3:
    education_checkbox_states = {}  # to track which are selected

    for education in cv_info_data["education"]:
        col1, col2 = st.columns([1, 40])

        with col1:
            education_checkbox_states[education] = st.checkbox(label="", key=f"todo_{education}")

        with col2:
            with st.container(border=False):
                st.write("#### " + education.upper())
                st.write("##### " + str(cv_info_data["education"][education]["dates"]))
                st.text("\n".join(cv_info_data["education"][education]["subjects"]))
    save_button = st.button("Save this section", icon="💾", on_click=saveData, use_container_width=True, key="save_education")

# QUALIFICATIONS/CERTIFICATES TAB
with tab4:
    qualification_introduction = st.text_area("A quick bit about the experience of getting these qualifications...", cv_info_data["certificates/qualifications"]["intro"], height="content")
    qualification_checkbox_states = {}
    for qualification in cv_info_data["certificates/qualifications"]["options"]:
        label_text = str(qualification[0]) + " - " + str(qualification[1])
        qualification_checkbox_states[qualification[0]] = st.checkbox(label=label_text, key=f"todo_{qualification}")
    col1, col2 = st.columns(2)
    with col1:
        create_button = st.button("Add new qualification", icon="➕", on_click=createNew, args=("qualification",), use_container_width=True, type="primary", key="add_qualification")
    with col2:
        save_button = st.button("Save this section", icon="💾", on_click=saveData, use_container_width=True, key="save_qualification")

with tab5:
    employment_checkbox_states = {}
    for employment in cv_info_data["employment"]:
        col1, col2 = st.columns([1, 40])

        with col1:
            employment_checkbox_states[employment] = st.checkbox(label="", key=f"todo_{employment}")

        with col2:
            with st.container(border=False):
                st.write("#### " + employment.title())
                st.write("##### " + str(cv_info_data["employment"][employment]["role"]).title() + " ----- " + str(cv_info_data["employment"][employment]["dates"]))
                st.text_area("", cv_info_data["employment"][employment]["description"], label_visibility="collapsed", height="content")
    col1, col2 = st.columns(2)
    with col1:
        create_button = st.button("Add new employment", icon="➕", on_click=createNew, args=("employment",), use_container_width=True, type="primary", key="add_employment")
    with col2:
        save_button = st.button("Save this section", icon="💾", on_click=saveData, use_container_width=True, key="save_employemnt")


# WORK EXPERIENCE/VOLUNTEERING TAB
with tab6:
    we_v_checkbox_states = {}
    for we_v in cv_info_data["work experience/volunteering"]:
        col1, col2 = st.columns([1, 40])

        with col1:
            we_v_checkbox_states[we_v] = st.checkbox(label="", key=f"todo_{we_v}")

        with col2:
            with st.container(border=False):
                st.write("#### " + we_v.title())
                st.write("##### " + str(cv_info_data["work experience/volunteering"][we_v]["role"]).title() + " ----- " + str(
                    cv_info_data["work experience/volunteering"][we_v]["dates"]))
                st.text_area("", cv_info_data["work experience/volunteering"][we_v]["description"], label_visibility="collapsed",
                             height="content")
    col1, col2 = st.columns(2)
    with col1:
        create_button = st.button("Add new volunteering", icon="➕", on_click=createNew, args=("volunteering",), use_container_width=True, type="primary", key="add_volunteering")
    with col2:
        save_button = st.button("Save this section", icon="💾", on_click=saveData, use_container_width=True, key="save_volunteering")


# REFERENCES TAB
with tab7:
    st.write(cv_info_data["references"])


# SKILLS TAB
with tab8:
    skills = st.multiselect("Skills", cv_info_data["skills"], accept_new_options=True)
    save_button = st.button("Save this section", icon="💾", on_click=saveData, use_container_width=True, key="save_skills")


# HOBBIES TAB
with tab9:
    free_time = st.multiselect("Interests/hobbies", cv_info_data["interests/hobbies"], accept_new_options=True)
    save_button = st.button("Save this section", icon="💾", on_click=saveData, use_container_width=True, key="save_hobbies")


# SUBMIT
with tab10:
    st.info("Ensure all information is correct before clicking the button below!")
    createCV = st.button("Create CV", use_container_width=True, type="primary")

    if createCV:
        with st.spinner("Building your CV..."):
            try:
                url = update_cv("https://docs.google.com/document/d/1kc0D6zvas_hv45GodWxWZR4tH3HHIyQgaHfbycCvt2s/edit?tab=t.0", json_file=CV_TEMPLATE)
                st.success("Done! View it at " + url)
            except Exception as e:
                st.error(f"Something went wrong: {e}")


# PROGRESS BAR
st.divider()

try:
    current_tab_index = headings.index(st.session_state.my_tabs)
    progress_bar_value = int(((current_tab_index + 1) / len(headings)) * 100)
except (AttributeError, ValueError):
    progress_bar_value = 10

progress_bar = st.progress(progress_bar_value, text=f"{progress_bar_value}% complete")

