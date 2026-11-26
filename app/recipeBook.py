# IMPORTS
import streamlit as st
from pathlib import Path
import json
from io import BytesIO
import requests
from PIL import Image, ImageOps
import base64

# PAGE SETUP
st.set_page_config(page_title="Recipe Book", layout="wide")

# if st.session_state.get("image_errors"):
#     with st.expander("Image problems", expanded=True):
#         st.json(st.session_state["image_errors"])

# PRE-MADE SELECT OPTIONS
recipe_type_options = {
    "Breakfast" : "green", 
    "Lunch" : "yellow", 
    "Dinner" : "blue", 
    "Drinks" : "orange"}
recipe_cuisine_options = []
CARD_SIZE = (600, 400)    # 3:2 for the home grid
HERO_SIZE = (1000, 800)   # 5:4 for the detail view
GRID_COLUMNS = 3

# LOADING THE RECIPE DATA JSON FILE

ROOT_DIR = Path(__file__).resolve().parent.parent
recipe_data_file_path = ROOT_DIR / "recipeBookData" / "recipes.json"
with open(recipe_data_file_path, "r") as recipe_data_file:
    recipe_data = json.load(recipe_data_file)


# WRITE JSON STRAND FROM PY FILE TO JSON FILE
def rewriteToJson():
    with open(recipe_data_file_path, "w") as recipe_data_file:
        json.dump(recipe_data, recipe_data_file, indent=4)


# IMAGE LOADER: fetches (URL or local path), crops to an exact size, caches the result
@st.cache_data(show_spinner=False)
def fetch_and_crop(source, size, focus=(0.5, 0.5)):
    if source.startswith("data:image"):
        encoded = source.split(",", 1)[1]
        img = Image.open(BytesIO(base64.b64decode(encoded)))
    elif source.startswith(("http://", "https://")):
        response = requests.get(source, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
    else:
        img = Image.open(source)
    img = ImageOps.exif_transpose(img).convert("RGB")
    return ImageOps.fit(img, size, Image.LANCZOS, centering=focus)


def load_image(source, size, focus=(0.5, 0.5)):
    try:
        return fetch_and_crop(source, size, focus)
    except Exception as error:
        st.session_state.setdefault("image_errors", {})[source] = repr(error)
        return Image.new("RGB", size, "#F0F2F6")


# SMALL HELPERS
def format_time(total_mins):
    hrs, mins = divmod(total_mins, 60)
    if hrs == 0:
        return f"{mins}mins"
    if mins == 0:
        return f"{hrs}hrs"
    return f"{hrs}hrs {mins}mins"


def split_lines(text):
    return [line.strip() for line in text.splitlines() if line.strip()]


# RECIPE ADDER FUNCTION
@st.dialog("Add new recipe", width="large")
def recipe_adder():
    col1, col2, col3 = st.columns(3)
    with col1:
        recipe_title = st.text_input("Recipe title")
        recipe_image = st.text_input("Recipe image URL")
        recipe_type = st.selectbox("Recipe type", recipe_type_options, accept_new_options=True)
        recipe_rating = st.number_input("Rating", min_value=1, max_value=5)
        recipe_timing = st.slider("Prep & cook time (mins)", min_value=5, max_value=360, step=5)
        recipe_serving = st.number_input("Serves", min_value=1, max_value=10)
        recipe_cuisine = st.multiselect("Cuisine", recipe_cuisine_options, accept_new_options=True)

    with col2:
        recipe_ingredients = st.text_area("Ingredients (one per line)", height="stretch")

    with col3:
        recipe_instructions = st.text_area("Instructions (one step per line)", height="stretch")

    if st.button("Save", icon="💾"):
        if recipe_type not in recipe_type_options:
            recipe_type_options.append(recipe_type)

        recipe_data[recipe_title] = {
            "Image": recipe_image,
            "Recipe type": recipe_type,
            "Rating": recipe_rating,
            "Prep & cook time": recipe_timing,
            "Serves": recipe_serving,
            "Cuisine": recipe_cuisine,
            "Ingredients": split_lines(recipe_ingredients),
            "Instructions": split_lines(recipe_instructions),
        }

        rewriteToJson()
        st.rerun()


# DETAIL VIEW (shown after clicking "View recipe")
def show_recipe_detail(name):
    recipe = recipe_data[name]

    if st.button("All recipes", icon=":material/arrow_back:"):
        st.session_state["selected"] = None
        st.rerun()

    st.title(name)
    with st.container(horizontal=True):
        st.badge(recipe["Recipe type"], color=recipe_type_options[recipe["Recipe type"]])
        st.badge(recipe["Cuisine"], color="gray")

    left, right = st.columns([1.1, 1], gap="large")

    with left:
        st.image(load_image(recipe["Image"], HERO_SIZE), use_container_width=True)
        m1, m2, m3 = st.columns(3)
        m1.metric("Time", format_time(recipe["Prep & cook time"]))
        m2.metric("Serves", recipe["Serves"])
        m3.metric("Rating", str(recipe["Rating"]) + " ⭐️'s")

    with right:
        with st.container(border=True):
            ingredients_tab, method_tab = st.tabs(["Ingredients", "Method"])
            with ingredients_tab:
                for i, ingredient in enumerate(recipe["Ingredients"]):
                    st.checkbox(ingredient, key=f"ing_{name}_{i}")
            with method_tab:
                for step_number, step in enumerate(recipe["Instructions"], start=1):
                    st.markdown(f"**{step_number}.** {step}")


# IF A RECIPE IS SELECTED, SHOW IT AND STOP (skips the home screen below)
selected = st.session_state.get("selected")
if selected in recipe_data:
    show_recipe_detail(selected)
    st.stop()


# HEADING CONTENT
with st.container(horizontal=True, vertical_alignment="center", horizontal_alignment="distribute"):
    st.title("Recipe Book 🍛", width="content")
    if st.button("Add new recipe", type="primary", icon=":material/add:"):
        recipe_adder()


# SEARCH AND FILTER SECTION
with st.container(horizontal=True):
    recipe_search = st.text_input(
        "Search for...",
        label_visibility="collapsed",
        placeholder="Search",
        icon=":material/search:",
        width=300,
    )
    recipe_type_filter = st.pills("Recipe Type", recipe_type_options, label_visibility="collapsed")


# FILTER RECIPES BASED ON SEARCH INPUT
clean_query = (recipe_search or "").strip().casefold()

displayed_recipes = [
    name for name, info in recipe_data.items()
    if (not clean_query or clean_query in name.casefold())
    and (not recipe_type_filter or info["Recipe type"] == recipe_type_filter)
]


# DISPLAY MATCHING CARDS IN A GRID
if not displayed_recipes:
    st.info(f"No recipes found matching '{recipe_search}'.")
else:
    for row_start in range(0, len(displayed_recipes), GRID_COLUMNS):
        row_recipes = displayed_recipes[row_start:row_start + GRID_COLUMNS]
        columns = st.columns(GRID_COLUMNS)  # always 3, so a short last row keeps card width

        for column, name in zip(columns, row_recipes):
            info = recipe_data[name]
            with column.container(border=True):
                st.image(load_image(info["Image"], CARD_SIZE), use_container_width=True)
                st.subheader(name)
                st.caption(
                    f"{info['Rating'] * '⭐️'}  ·  Serves {info['Serves']}  ·  "
                    f"{format_time(info['Prep & cook time'])}"
                )
                if st.button("View recipe", key=f"view_{name}", use_container_width=True):
                    st.session_state["selected"] = name
                    st.rerun()