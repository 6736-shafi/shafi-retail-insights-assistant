from typing import TypedDict, Annotated, List, Union
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from src.backend.data_loader import DataLoader
import pandas as pd
import os

# Define the State
class AgentState(TypedDict):
    """
    Represents the state of the agent workflow.
    This dictionary is passed between nodes in the graph, carrying the query, SQL, data, and error status.
    """
    user_query: str
    schema_info: str
    sql_query: str
    data: Union[pd.DataFrame, str, None]
    error: str
    retries: int
    final_response: str

class LangGraphAgent:
    """
    Implementation of the agent using LangGraph.
    Uses a StateGraph to define a cyclic workflow with self-correction capabilities.
    Nodes: Resolve -> Extract -> Validate -> Response.
    """
    def __init__(self, data_paths):
        self.data_loader = DataLoader(data_paths)
        self.data_loader.load_data()
        
        # Initialize LLM
        api_key = os.getenv("GOOGLE_API_KEY")
        self.llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", google_api_key=api_key)
        
        # Build Graph
        self.app = self._build_graph()

    def _build_graph(self):
        """
        Constructs the StateGraph.
        Defines nodes and edges, including the conditional logic for retries.
        """
        workflow = StateGraph(AgentState)

        # Define Nodes
        workflow.add_node("resolve_query", self.resolve_query)
        workflow.add_node("extract_data", self.extract_data)
        workflow.add_node("validate_data", self.validate_data)
        workflow.add_node("generate_response", self.generate_response)

        # Define Edges
        workflow.set_entry_point("resolve_query")
        
        workflow.add_edge("resolve_query", "extract_data")
        
        # Conditional Edge for Retry Loop
        workflow.add_conditional_edges(
            "extract_data",
            self.check_execution,
            {
                "retry": "resolve_query",
                "success": "validate_data",
                "failed": "generate_response" # If retries exhausted, go to response (to say sorry)
            }
        )
        
        workflow.add_edge("validate_data", "generate_response")
        workflow.add_edge("generate_response", END)

        return workflow.compile()

    # --- Node Functions ---

    def resolve_query(self, state: AgentState):
        """
        Node: Resolve Query
        Generates SQL from the user query.
        If 'error' is present in the state, it switches to 'Fix Mode' to correct the previous SQL.
        """
        print("--- Node: Resolve Query ---")
        schema = self.data_loader.get_schema_info()
        query = state["user_query"]
        error = state.get("error", "")
        
        if error:
            # Fix mode
            prompt = f"""
            You are a SQL expert. The previous query failed.
            Schema: {schema}
            User Query: "{query}"
            Error: {error}
            Previous SQL: {state["sql_query"]}
            Fix the SQL. Return ONLY the SQL.
            """
        else:
            # New query mode
            prompt = f"""
            You are a SQL expert. Convert to DuckDB SQL.
            Schema: {schema}
            User Query: "{query}"
            Return ONLY the SQL.
            """
            
        response = self.llm.invoke(prompt).content
        # Clean SQL
        sql = response.replace("```sql", "").replace("```", "").strip()
        return {"sql_query": sql, "schema_info": schema}

    def extract_data(self, state: AgentState):
        print("--- Node: Extract Data ---")
        sql = state["sql_query"]
        try:
            data = self.data_loader.query(sql)
            return {"data": data, "error": ""}
        except Exception as e:
            return {"error": str(e), "retries": state.get("retries", 0) + 1}

    def check_execution(self, state: AgentState):
        """
        Conditional Logic:
        Checks if the data extraction was successful.
        If error exists and retries < 3, routes back to 'resolve_query' (Retry).
        Otherwise, proceeds to validation or response.
        """
        if state.get("error"):
            if state.get("retries", 0) < 3:
                print(f"--- Retry {state['retries']} ---")
                return "retry"
            else:
                return "failed"
        return "success"

    def validate_data(self, state: AgentState):
        print("--- Node: Validate Data ---")
        data = state["data"]
        if data is None or (isinstance(data, pd.DataFrame) and data.empty):
            return {"data": None} # Mark as empty
        return {"data": data}

    def generate_response(self, state: AgentState):
        print("--- Node: Generate Response ---")
        data = state.get("data")
        error = state.get("error")
        
        if error:
            return {"final_response": f"I couldn't answer that. Error: {error}"}
        
        if data is None:
            return {"final_response": "No data found matching your query."}
            
        prompt = f"""
        Answer the user's question based on the data.
        User Query: "{state['user_query']}"
        Data: {data.to_string() if isinstance(data, pd.DataFrame) else str(data)}
        """
        response = self.llm.invoke(prompt).content
        return {"final_response": response}

    # --- Public Interface (Matching Orchestrator) ---
    
    def process_query(self, user_query: str):
        initial_state = {"user_query": user_query, "retries": 0, "error": ""}
        result = self.app.invoke(initial_state)
        return result["final_response"]

    def generate_summary(self):
        """Generates a comprehensive summary of the dataset using predefined queries."""
        queries = {
            "Total Sales": "SELECT SUM(Amount) FROM sales_data",
            "Sales by Year": "SELECT Year, SUM(Amount) FROM sales_data GROUP BY Year ORDER BY Year",
            "Top 5 Categories": "SELECT Category, SUM(Amount) FROM sales_data GROUP BY Category ORDER BY 2 DESC LIMIT 5",
            "Sales by Source": "SELECT Source, SUM(Amount) FROM sales_data GROUP BY Source"
        }
        
        results = {}
        for title, sql in queries.items():
            try:
                # Use the data loader directly
                df = self.data_loader.query(sql)
                results[title] = df.to_string() if not df.empty else "No data"
            except Exception as e:
                results[title] = f"Error: {e}"
        
        # Synthesize
        prompt = f"""
        You are a senior business analyst. Generate a concise, human-readable executive summary of the sales performance based on the following data:
        
        {results}
        
        Focus on:
        1. Total Sales and growth (if visible in Year data).
        2. Top performing categories.
        3. Any significant trends.
        
        Format the output with clear headings and bullet points.
        """
        return self.llm.invoke(prompt).content
