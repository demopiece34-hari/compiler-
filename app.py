import streamlit as st
from tamilscript import run_tamilscript, TamilScriptError

st.set_page_config(page_title="TamilScript Online IDE", page_icon="💻", layout="wide")
st.title("💻 TamilScript Online IDE")
st.caption("Write your own TamilScript program, run it, and view the output.")

STARTER_CODE = r"""
# My first TamilScript program
vei a = 10
vei b = 20

sollu "Vanakkam from TamilScript!"
sollu a + b

irunthal a < b {
    sollu "a is smaller than b"
} illaiyel {
    sollu "a is greater than or equal to b"
}

vei i = 1
thirumba i <= 3 {
    sollu i
    i = i + 1
}
"""

if "source_code" not in st.session_state:
    st.session_state.source_code = STARTER_CODE
if "last_output" not in st.session_state:
    st.session_state.last_output = None
if "last_error" not in st.session_state:
    st.session_state.last_error = None

left, right = st.columns([3, 2], gap="large")

with left:
    st.subheader("Code Editor")
    source = st.text_area(
        "Write TamilScript code",
        key="source_code",
        height=420,
        label_visibility="collapsed",
        help="Use English-letter TamilScript keywords. Separate statements with newlines.",
    )
    run_clicked = st.button("▶ Run TamilScript", type="primary", use_container_width=True)
    reset_clicked = st.button("↺ Load example", use_container_width=True)

with right:
    st.subheader("Output")
    if run_clicked:
        output_lines = []
        try:
            run_tamilscript(source, output_function=lambda value: output_lines.append(str(value)))
            st.session_state.last_output = "\n".join(output_lines) if output_lines else "(Program finished with no output.)"
            st.session_state.last_error = None
        except TamilScriptError as exc:
            st.session_state.last_output = None
            st.session_state.last_error = str(exc)
        except Exception as exc:
            st.session_state.last_output = None
            st.session_state.last_error = f"Unexpected interpreter error: {type(exc).__name__}: {exc}"

    if reset_clicked:
        st.session_state.source_code = STARTER_CODE
        st.session_state.last_output = None
        st.session_state.last_error = None
        st.rerun()

    if st.session_state.last_error:
        st.error("TamilScript error")
        st.code(st.session_state.last_error, language="text")
    elif st.session_state.last_output is not None:
        st.success("Program executed")
        st.code(st.session_state.last_output, language="text")
    else:
        st.info("Click Run TamilScript to see the program output here.")

with st.expander("TamilScript syntax guide"):
    st.markdown("""
- `vei name = expression` — declare a variable
- `name = expression` — update an existing variable
- `sollu expression` — print output
- `irunthal condition { ... } illaiyel { ... }` — if/else
- `thirumba condition { ... }` — while loop
- Operators: `+`, `-`, `*`, `/`, `==`, `!=`, `<`, `<=`, `>`, `>=`
- Strings: `"Hello"` or `'Hello'`
- Comments: lines beginning with `#`
""")

st.caption("Educational interpreter. Do not enter passwords or private information.")
