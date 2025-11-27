# Retail Insights Assistant - Technical Documentation

## 1. Assumptions

*   **Data Consistency**: The system assumes that the CSV files in the `data/` directory (`Amazon Sale Report.csv`, etc.) maintain the same column names and data types as the sample dataset provided. Drastic schema changes would require updating the `DataLoader`.
*   **Currency**: All monetary values in the source data are assumed to be in **INR (Indian Rupee)** unless a specific currency column exists and is handled.
*   **Business Logic**:
    *   "Cancelled" orders are excluded from Revenue calculations but might be tracked for "Cancellation Rate".
    *   "Shipped" status implies a successful sale for revenue recognition purposes in this POC.
*   **Single User**: The application is currently designed as a single-tenant prototype. It does not handle concurrent user sessions with isolated memory states (though Streamlit handles basic session isolation).

---

## 2. Limitations

*   **Context Window**: While Gemini Flash has a large context window, extremely complex queries requiring the retrieval of thousands of rows might be truncated or exceed token limits. The current "Text-to-SQL" approach mitigates this by aggregating data *before* sending it to the LLM, but raw data inspection is limited.
*   **Statelessness (Custom Agent)**: The "Custom" and "CrewAI" agent implementations are largely stateless per query. They do not "remember" the result of the previous query for follow-up questions (e.g., "Drill down into that") unless explicitly passed in the conversation history (which is partially implemented in the UI but limited in the backend logic).
*   **Latency**:
    *   **CrewAI**: The CrewAI implementation is slower (10-20s) due to its sequential "ReAct" (Reason+Act) loop and multiple agent handoffs.
    *   **Cold Starts**: The first query might be slower as the LLM connection is established.
*   **Error Handling**: While there is a self-correction loop for SQL errors, complex logical errors (e.g., querying the wrong table for a vague metric) might still yield incorrect results without a user warning.

---

## 3. Possible Improvements (Scalability & Features)

### A. RAG & Vector Search (For 100GB+ Scale)
*   **Problem**: As the number of tables grows (e.g., 1000+ tables), passing the entire schema to the LLM becomes impossible.
*   **Solution**: Implement a **Vector Database** (Pinecone/Chroma).
    *   Index table names and column descriptions.
    *   For each user query, perform a semantic search to retrieve only the top 5 relevant tables.
    *   Pass only those 5 schemas to the LLM for SQL generation.

### B. Caching Layer
*   **Problem**: Repeated queries (e.g., "Total Revenue") cost money and time.
*   **Solution**: Implement **Redis** caching.
    *   Hash the natural language query (or the generated SQL).
    *   Store the result dataframe/summary.
    *   Serve instant results for identical queries within a 24-hour window.

### C. Advanced Authentication & Security
*   **Problem**: No access control.
*   **Solution**: Integrate **Auth0** or **Google OAuth**.
    *   Implement Row-Level Security (RLS) in the database so users only see data for their specific region/department.

### D. CI/CD & Monitoring
*   **Solution**:
    *   Add **LangSmith** or **Arize Phoenix** to trace agent thoughts and debug failures.
    *   Set up GitHub Actions to run `test_pipeline.py` on every commit.
