# Implementation Details & Project Structure

This document provides a deep dive into the codebase structure and the technical implementation of the three multi-agent frameworks used in the **Retail Insights Assistant**.

## 📂 Project Structure

```text
RetailInsightsAssistant/
├── src/
│   ├── backend/                 # Core logic and agent implementations
│   │   ├── agents.py            # 1. Custom Orchestrator Implementation
│   │   ├── langgraph_agent.py   # 2. LangGraph Implementation
│   │   ├── crewai_agent.py      # 3. CrewAI Implementation
│   │   ├── data_loader.py       # Data ingestion (CSV -> DuckDB)
│   │   └── llm_client.py        # Wrapper for Google Gemini API
│   └── ui/
│       └── app.py               # Streamlit Frontend Application
├── data/                        # Directory for input CSV files
├── architecture_presentation.md # Architecture documentation
├── requirements.txt             # Python dependencies
└── README.md                    # General overview
```

---

## ✨ Key Features Implemented

### 1. Interactive Visualization Tab
*   **Goal**: Provide immediate visual insights without needing to ask questions.
*   **Implementation**:
    *   Added a dedicated "📈 Visualization" tab in Streamlit.
    *   **Backend**: Implemented `get_visualization_data()` in all agent classes (`Orchestrator`, `LangGraphAgent`, `CrewAIAgent`).
    *   **Logic**: Executes three pre-defined SQL queries:
        1.  *Sales by Year* (Line Chart)
        2.  *Top 10 Categories* (Bar Chart)
        3.  *Sales by Source* (Bar Chart)
    *   **UI**: Renders interactive charts using Streamlit's native charting libraries.

### 2. Automated Summarization
*   **Goal**: Generate a text-based executive summary of the entire dataset.
*   **Implementation**:
    *   **Backend**: `generate_summary()` method runs 4-5 aggregate queries (Total Sales, Top Categories, etc.).
    *   **Synthesis**: Feeds these raw numbers into the LLM with a specific prompt to act as a "Senior Business Analyst".
    *   **Output**: Produces a structured markdown report with bullet points and trends.

### 3. Dynamic Framework Switching
*   **Goal**: Allow users/developers to compare different agent architectures side-by-side.
*   **Implementation**:
    *   **Sidebar Control**: A radio button allows hot-swapping the backend engine.
    *   **State Management**: `st.session_state` preserves the loaded data path but re-initializes the selected agent class (`Orchestrator` vs `LangGraphAgent` vs `CrewAIAgent`) on the fly.

### 4. Multi-Source Data Ingestion
*   **Goal**: Handle disparate data formats (Sales, Stock, Pricing) seamlessly.
*   **Implementation**:
    *   **Smart Detection**: `DataLoader` inspects column signatures (e.g., presence of `Fulfilment` vs `GROSS AMT`) to identify the file type.
    *   **Normalization**: Standardizes different schemas (renaming columns to `Date`, `Amount`, `Qty`, `SKU`) into a unified `sales_data` table in DuckDB.

---

## 🧠 Multi-Agent Frameworks

The core innovation of this project is the ability to switch between three distinct agent architectures. All frameworks share the same `DataLoader` and `LLMClient` but differ in how they orchestrate the reasoning process.

### 1. Custom Orchestrator (`src/backend/agents.py`)
*   **Type**: Manual / Imperative Control Flow.
*   **Description**: A Python class (`Orchestrator`) that manually manages the sequence of operations. It explicitly calls specific agent methods in a fixed order.
*   **Workflow**:
    1.  **Query Resolution**: `QueryResolutionAgent` translates NL to SQL.
    2.  **Extraction**: `DataExtractionAgent` runs the SQL on DuckDB.
    3.  **Validation**: `ValidationAgent` checks if data is empty.
    4.  **Response**: `ResponseAgent` generates the final answer.
*   **Pros**: Simple, easy to debug, full control.
*   **Cons**: Rigid, hard to implement complex retry logic or loops.

### 2. LangGraph (`src/backend/langgraph_agent.py`)
*   **Type**: State Machine / Graph-Based.
*   **Description**: Uses `langgraph` to define a cyclic graph where nodes are functions and edges are control flow. It maintains a global `AgentState`.
*   **Key Feature: Self-Correction Loop**:
    *   If the **Extract Data** node fails (SQL error), the graph follows a conditional edge back to **Resolve Query** with the error message.
    *   The agent attempts to fix the SQL up to 3 times before giving up.
*   **Nodes**: `resolve_query` -> `extract_data` -> `validate_data` -> `generate_response`.
*   **Pros**: Robust error handling, stateful, scalable complexity.

### 3. CrewAI (`src/backend/crewai_agent.py`)
*   **Type**: Role-Playing Team.
*   **Description**: Uses `crewai` to define autonomous agents with specific "Roles", "Goals", and "Backstories". Agents collaborate to complete "Tasks".
*   **The Crew**:
    *   **Query Resolution Specialist**: Expert in SQL dialects.
    *   **Database Administrator**: Has the `Execute SQL` tool.
    *   **Data Validator**: Ensures data quality.
    *   **Retail Data Analyst**: Synthesizes insights.
*   **Workflow**: Sequential process (`Process.sequential`) where the output of one task is the context for the next.
*   **Pros**: High-quality reasoning due to role-playing, modular agent definitions.

---

## 🛠️ Shared Components

### Data Loader (`src/backend/data_loader.py`)
*   **Engine**: **DuckDB** (In-memory OLAP database).
*   **Function**: Scans the `data/` directory, detects CSV files, and loads them into DuckDB tables.
*   **Schema Inference**: Automatically detects column names and types to inject into LLM prompts.

### UI (`src/ui/app.py`)
*   **Framework**: **Streamlit**.
*   **Features**:
    *   **Chat Interface**: `st.chat_message` for conversation.
    *   **Sidebar**: Configuration (Framework selection, API Key).
    *   **Visualization Tab**: Uses `st.line_chart` and `st.bar_chart` to render plots from `get_visualization_data()`.
