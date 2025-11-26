import streamlit as st
import pandas as pd
import os
import sys

# Add src to path so we can import backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.backend.agents import Orchestrator

st.set_page_config(page_title="Retail Insights Assistant", layout="wide")

# --- UI Layout & Configuration ---
st.title("🛍️ Retail Insights Assistant")
st.markdown("GenAI-powered analytics for your sales data.")

# Sidebar for configuration and file upload
with st.sidebar:
    st.header("Data Setup")
    uploaded_files = st.file_uploader("Upload Sales CSV(s)", type=["csv"], accept_multiple_files=True)
    
    api_key = st.text_input("Enter Google API Key", type="password")
    if api_key:
        os.environ["GOOGLE_API_KEY"] = api_key

    st.divider()
    framework_choice = st.radio("Select Agent Framework", ["Custom (Python)", "LangGraph", "CrewAI"])
    
    with st.expander("❓ Sample Questions"):
        st.markdown("""
        **Sales Data (Amazon/International):**
        - What is the total revenue by year?
        - Which city has the highest sales?
        - Compare sales of 'Kurta' vs 'Set'.
        - What is the monthly sales trend?
        
        **Stock Data (Sale Report):**
        - *Requires loading Stock file*
        - Which SKU has the lowest stock?
        - Show products with Red color.
        
        **Pricing (May-2022):**
        - *Requires loading Pricing file*
        - What is the average MRP for Kurtas?
        - Compare Amazon MRP vs Flipkart MRP.
        """)

# Main area
if uploaded_files:
    # Save uploaded files temporarily
    data_paths = []
    if not os.path.exists("temp"):
        os.makedirs("temp")
        
    for uploaded_file in uploaded_files:
        path = os.path.join("temp", uploaded_file.name)
        with open(path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        data_paths.append(path)
        
    try:
        # --- Backend Initialization ---
        # Initialize the Orchestrator (Agent Manager) only if not already present or if framework changed.
        # This prevents reloading the heavy agents on every interaction.
        if "orchestrator" not in st.session_state or st.session_state.get("current_framework") != framework_choice:
            with st.spinner(f"Initializing {framework_choice} Agent..."):
                if framework_choice == "LangGraph":
                    from src.backend.langgraph_agent import LangGraphAgent
                    st.session_state.orchestrator = LangGraphAgent(data_paths)
                elif framework_choice == "CrewAI":
                    from src.backend.crewai_agent import CrewAIAgent
                    st.session_state.orchestrator = CrewAIAgent(data_paths)
                else:
                    from src.backend.agents import Orchestrator
                    st.session_state.orchestrator = Orchestrator(data_paths)
                
                st.session_state.current_framework = framework_choice
                st.success(f"Loaded data using {framework_choice}!")

        # Tabs for different modes
        tab1, tab2 = st.tabs(["💬 Chat Q&A", "📊 Summarization"])

        with tab1:
            st.subheader("Ask questions about your data")
            
            # --- Chat Interface ---
            # Initialize Session State for Chat History to maintain context across reruns
            if "messages" not in st.session_state:
                st.session_state.messages = []

            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            if prompt := st.chat_input("Ex: Which city has the highest sales?"):
                # 1. Add User Message to History
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("Analyzing..."):
                        # 2. Process Query via Backend Agent
                        response = st.session_state.orchestrator.process_query(prompt)
                        st.markdown(response)
                        # 3. Add Assistant Response to History
                        st.session_state.messages.append({"role": "assistant", "content": response})

        with tab2:
            st.subheader("Automated Insights")
            if st.button("Generate Summary"):
                with st.spinner("Generating summary..."):
                    response = st.session_state.orchestrator.generate_summary()
                    st.markdown(response)

    except Exception as e:
        st.error(f"Error initializing system: {e}")
        
else:
    st.info("Please upload a CSV file to begin.")
    
    # Optional: Load default data if available
    if st.button("Load Demo Data (Amazon Sale Report.csv)"):
        demo_path = "data/Amazon Sale Report.csv"
        if os.path.exists(demo_path):
            with st.spinner("Loading demo data..."):
                st.session_state.orchestrator = Orchestrator(demo_path)
                st.success("Demo data loaded! Switch to Chat tab.")
                st.rerun()
        else:
            st.error("Demo data not found.")
