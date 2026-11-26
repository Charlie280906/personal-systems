# IMPORTS
import streamlit as st
from pathlib import Path
import json
from st_keyup import st_keyup

# PAGE SETUP
st.set_page_config(
    page_title="Recipe Book",
    layout="wide"
)

# PRE-MADE SELECT OPTIONS
recipe_type_options = ["Breakfast", "Lunch", "Dinner", "Drinks"]
recipe_cuisine_options = []

# LOADING THE RECIPE DATA JSON FILE
recipe_data_file_path = Path("../recipeBookData") / "recipes.json"
with open(recipe_data_file_path, 'r') as recipe_data_file:
    recipe_data = json.load(recipe_data_file)


# WRITE JSON STRAND FROM PY FILE TO JSON FILE
def rewriteToJson():
    with open(recipe_data_file_path, "w") as recipe_data_file:
        json.dump(recipe_data, recipe_data_file, indent=4)


# HEADING CONTENT
with (st.container(horizontal=True, vertical_alignment="center", horizontal_alignment="distribute")):
    st.title("Recipe Book 🍛")


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
            recipe_ingredients = st.text_area("Ingredients", height="stretch")

        with col3:
            recipe_instructions = st.text_area("Instructions", height="stretch")

        if st.button("Save", icon="💾"):
            # CHECK FOR NEW MEAL TYPES
            # TODO: COMPLETE THIS FEATURE
            if recipe_type not in recipe_type_options:
                recipe_type_options.append(recipe_type)

            # SEPARATING INGREDIENTS TO INDIVIDUAL STRINGS
            formatted_ingredients = []
            temp_holder = ""
            for index in range(0, len(list(recipe_ingredients))):
                item = list(recipe_ingredients)[index]
                if item == "\n":
                    formatted_ingredients.append(temp_holder)
                    temp_holder = ""
                elif index == len(list(recipe_ingredients)) - 1:
                    temp_holder = temp_holder + item
                    formatted_ingredients.append(temp_holder)
                    temp_holder = ""
                else:
                    temp_holder = temp_holder + item

            # SEPARATING INSTRUCTIONS TO INDIVIDUAL LINES
            formatted_instructions = []
            temp_holder = ""
            for index in range(0, len(list(recipe_instructions))):
                item = list(recipe_instructions)[index]
                if item == "\n":
                    formatted_instructions.append(temp_holder)
                    temp_holder = ""
                elif index == len(list(recipe_instructions)) - 1:
                    temp_holder = temp_holder + item
                    formatted_instructions.append(temp_holder)
                    temp_holder = ""
                else:
                    temp_holder = temp_holder + item

            # ADDING THE NEW RECIPE TO THE JSON DATA
            recipe_data[recipe_title] = {
                "Image": recipe_image,
                "Recipe type": recipe_type,
                "Rating": recipe_rating,
                "Prep & cook time": recipe_timing,
                "Serves": recipe_serving,
                "Cuisine": recipe_cuisine,
                "Ingredients": formatted_ingredients,
                "Instructions": formatted_instructions
            }

            rewriteToJson()
            st.rerun()


    if "recipe_adder" not in st.session_state:
        if st.button("Add new recipe", type="primary", icon=":material/add:"):
            recipe_adder()

    recipe_search = st_keyup(
        "Search for...",
        label_visibility="collapsed",
        placeholder="Search",
        debounce=200  # Waits 200ms after you stop typing so the UI doesn't flicker
    )

# GETS ALL THE NAMES OF RECIPES
all_recipes = list(recipe_data.keys())

# FILTER RECIPES BASED ON SEARCH INPUT
clean_query = recipe_search.strip().casefold()

if clean_query:
    displayed_recipes = [
        recipe for recipe in all_recipes
        if clean_query in recipe.casefold()
    ]
else:
    displayed_recipes = all_recipes

# DISPLAY MATCHING CONTAINERS
if not displayed_recipes:
    st.info(f"No recipes found matching '{recipe_search}'.")
else:
    for recipe in displayed_recipes:
        with st.container(border=True):
            st.image(recipe_data[recipe]["Image"])
            st.title(recipe)
            with st.container(horizontal_alignment="distribute", horizontal=True):
                st.subheader(recipe_data[recipe]["Rating"] * "⭐️")
                st.subheader(f"Serves: {recipe_data[recipe]['Serves']}")

                hrs = recipe_data[recipe]["Prep & cook time"] // 60
                mins = recipe_data[recipe]["Prep & cook time"] % 60
                if hrs == 0:
                    st.subheader(f"Time: {mins}mins")
                elif mins == 0:
                    st.subheader(f"Time: {hrs}hrs")
                else:
                    st.subheader(f"Time: {hrs}hrs {mins}mins")