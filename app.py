import streamlit as st
from tokenizer import Tokenizer
from parser import Parser
from queryengine import QueryEngine
from Pages import PageManager
from record import Schema
from Table import Table

st.set_page_config(
    page_title="SCARA SQL Engine",
    page_icon="🗃️",
    layout="centered",
)

st.markdown(
    """
    <style>
    .stTextInput input {
        font-family: monospace;
        font-size: 16px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🗃️ Mini SQL Interface")
st.caption("Scara SQL engine for educational purposes. Type your SQL query below and press ▶ Run.")

st.divider()


@st.cache_resource
def get_engine():
    pm = PageManager("lelouch.db")
    index_pm = PageManager("lelouch_id_index.db")
    schema = Schema([("id", "int"), ("name", "str", 20)])
    table = Table(pm, schema, index_page_manager=index_pm, index_column="id")
    return QueryEngine({"lelouch": table})


engine = get_engine()

col1, col2 = st.columns([4, 1])
with col1:
    query = st.text_input(
        "SQL Query",
        placeholder="SELECT id, name FROM lelouch WHERE id = 3721",
        label_visibility="collapsed",
    )
with col2:
    run_clicked = st.button("▶ Run", use_container_width=True)

if run_clicked:
    if not query.strip():
        st.warning("Type a query first.")
    else:
        try:
            tokens = Tokenizer(query).tokenize()
            statement = Parser(tokens).parse_statement()
            result = engine.execute(statement)
            st.success("Query executed successfully")
            if isinstance(result, list):
                st.dataframe(result, use_container_width=True)
            else:
                st.write(result)
        except Exception as e:
            st.error(f"Error: {e}")