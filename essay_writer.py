import streamlit as st
from src.essay_writer import EssayAgent
essay_agent=EssayAgent()
st.title("Essay Writer With Human Feedback")

if 'generate_clicked' not in st.session_state:
    st.session_state.generate_clicked = False

if 'next_clicked' not in st.session_state:
    st.session_state.next_clicked = False

def generate_button():
    st.session_state.next_clicked = False
    st.session_state.generate_clicked = True

def next_button():
    st.session_state.generate_clicked = False
    st.session_state.next_clicked = True

st.write("1. Planner -> 2. research_plan -> 3. generate -> 4. Feedback(reflect) -> 5.research_critique -> 6. generate", unsafe_allow_html=True)
col1,col2=st.columns(2)
with col1:
    topic = st.text_input(label='',placeholder="Type Topic Here.", )
with col2:
    btn1, btn2 = st.columns(2)
    with btn1:
        st.write("<br>",unsafe_allow_html=True)
        generate = st.button("Generate", on_click=generate_button)
    with btn2:
        st.write("<br>", unsafe_allow_html=True)
        next_step = st.button("Next", on_click=next_button)



if st.session_state.generate_clicked:
    # The message and nested widget will remain on the page
    results = []
    thread = {"configurable": {"thread_id": "1"}}
    for s in essay_agent.writer_agent.stream({
            'task': f"{topic}",
            "max_revisions": 2,
            "revision_number": 1,
        }, thread):
            results.append(s)
    results = results[0]
    node_name = list(results.keys())[0]
    state_key = list(results[node_name].keys())[0]

    #st.caption(node_name)
    st.text_area(label=node_name,value=results[node_name][state_key], height=300)
    update = st.button("Update")

if st.session_state.next_clicked:
    thread = {"configurable": {"thread_id": "1"}}
    if len(essay_agent.writer_agent.get_state(thread).next)>0:
        results = []        
        for s in essay_agent.writer_agent.stream(None,thread):
            results.append(s)
        results = results[0]
        node_name = list(results.keys())[0]
        state_key = list(results[node_name].keys())[0]
        st.text_area(label=node_name,value=results[node_name][state_key], height=300)
        update = st.button("Update")
    else:
        st.write("Finished")
