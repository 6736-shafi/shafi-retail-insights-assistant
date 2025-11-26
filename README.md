# Retail Insights Assistant

A GenAI-powered assistant for analyzing retail sales data, capable of answering ad-hoc business questions and generating executive summaries.

## 🚀 Features
*   **Conversational Q&A**: Ask questions about sales, stock, and pricing in plain English.
*   **Multi-Agent Backend**: Choose between **Custom**, **LangGraph**, or **CrewAI** frameworks.
*   **Automated Summarization**: One-click generation of KPI reports and insights.
*   **Data Engineering**: Robust pipeline handling multiple CSV sources (Sales, Stock, Pricing).

## 🛠️ Setup & Execution

### Prerequisites
*   Python 3.10+
*   Google Cloud API Key (Gemini)

### Installation
1.  **Clone/Unzip** the repository.
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Configure Environment**:
    *   Create a `.env` file (optional) or export your key:
        ```bash
        export GOOGLE_API_KEY="your_api_key_here"
        ```

### Running the App
```bash
streamlit run src/ui/app.py
```
The application will open at `http://localhost:8501`.

## 📝 Technical Notes

### Assumptions
1.  **Data Schema**: The system assumes the input CSVs match the schema of the provided sample data (Amazon Sales, International Sales, etc.).
2.  **Currency**: All monetary values are assumed to be in INR unless specified otherwise.
3.  **Single Tenant**: The current deployment assumes a single user session for simplicity.

### Limitations
1.  **Context Window**: Extremely large queries or massive intermediate SQL results might hit the LLM's token limit (though Gemini Flash has a large window).
2.  **Statelessness**: While the UI maintains chat history, the backend agents treat each query independently (except for the LangGraph implementation which has state).
3.  **Math Accuracy**: Complex multi-step calculations are offloaded to SQL (DuckDB) to ensure accuracy, as LLMs can struggle with direct arithmetic.

### Future Roadmap (Enterprise Scale)

1.  **Hybrid RAG for Schema Management**:
    *   *Current*: Full schema injection.
    *   *Future*: Use Vector DB (Pinecone) to index table metadata. Retrieve only top-5 relevant tables per query to handle 1000+ tables.

2.  **Intelligent Caching Layer**:
    *   *Current*: No caching.
    *   *Future*: Implement Redis to cache frequent SQL results (e.g., "Total Revenue"), reducing API costs and latency by 90%.

3.  **Security & Governance**:
    *   *Current*: Single-tenant.
    *   *Future*: Integrate OAuth2 and Row-Level Security (RLS) to restrict data access by region/role.

4.  **Automated Evaluation Pipeline**:
    *   *Future*: Integrate LangSmith/DeepEval to run regression tests on a "Golden Dataset" of Q&A pairs on every commit.

## 📂 Project Structure
*   `src/backend/`: Contains the agent implementations (Custom, LangGraph, CrewAI).
*   `src/ui/`: Streamlit application code.
*   `data/`: Directory for CSV datasets.
*   `architecture_presentation.md`: Detailed system design and scalability strategy.
