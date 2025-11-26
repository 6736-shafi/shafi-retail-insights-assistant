from .llm_client import LLMClient
from .data_loader import DataLoader
import pandas as pd

class Agent:
    def __init__(self, name, llm_client: LLMClient):
        self.name = name
        self.llm_client = llm_client

class QueryResolutionAgent(Agent):
    """
    Agent responsible for converting natural language queries into SQL.
    It uses the LLM to understand the user's intent and maps it to the database schema.
    """
    def resolve(self, user_query: str, schema_info: str) -> str:
        prompt = f"""
        You are a SQL expert. Convert the following natural language query into a DuckDB SQL query.
        The table name is 'sales_data'.
        
        Schema:
        {schema_info}
        
        User Query: "{user_query}"
        
        Rules:
        1. Return ONLY the SQL query.
        2. Do not include markdown formatting like ```sql or ```.
        3. Do not include any explanations or text outside the query.
        4. The query must be valid DuckDB SQL.
        """
        response = self.llm_client.generate_response(prompt)
        
        # Clean up response
        # Remove markdown code blocks if present
        import re
        match = re.search(r"```sql(.*?)```", response, re.DOTALL)
        if match:
            sql = match.group(1).strip()
        else:
            sql = response.replace("```sql", "").replace("```", "").strip()
            
        return sql

    def fix_query(self, user_query: str, schema_info: str, bad_sql: str, error_msg: str) -> str:
        """
        Self-Correction Mechanism:
        If a generated SQL query fails, this method is called to fix it.
        It provides the LLM with the original query, the failed SQL, and the error message.
        """
        prompt = f"""
        You are a SQL expert. The previous SQL query you generated for DuckDB failed.
        
        Schema:
        {schema_info}
        
        User Query: "{user_query}"
        
        Failed SQL:
        {bad_sql}
        
        Error Message:
        {error_msg}
        
        Task: Fix the SQL query to resolve the error. Ensure it is valid DuckDB SQL.
        Return ONLY the fixed SQL query.
        """
        response = self.llm_client.generate_response(prompt)
        
        import re
        match = re.search(r"```sql(.*?)```", response, re.DOTALL)
        if match:
            sql = match.group(1).strip()
        else:
            sql = response.replace("```sql", "").replace("```", "").strip()
        return sql

class DataExtractionAgent:
    """
    Agent responsible for executing SQL queries against the data source (DuckDB).
    It acts as the interface between the logic layer and the data layer.
    """
    def __init__(self, data_loader: DataLoader):
        self.data_loader = data_loader

    def extract(self, sql_query: str):
        print(f"Executing SQL: {sql_query}")
        return self.data_loader.query(sql_query)

class ValidationAgent:
    """
    Agent responsible for validating the results returned by the database.
    Ensures that the data is not empty and is in the expected format before passing it to the response agent.
    """
    def validate(self, data) -> bool:
        if data is None:
            return False
        if isinstance(data, pd.DataFrame):
            return not data.empty
        return False

class ResponseAgent(Agent):
    """
    Agent responsible for synthesizing the final natural language response.
    It takes the raw data and the user's original question to generate a business-friendly answer.
    """
    def summarize(self, user_query: str, data, sql_query: str) -> str:
        prompt = f"""
        You are a data analyst. Answer the user's question based on the data provided.
        
        User Query: "{user_query}"
        SQL Query Used: "{sql_query}"
        Data Retrieved:
        {data.to_string() if isinstance(data, pd.DataFrame) else str(data)}
        
        Provide a concise and helpful answer.
        """
        return self.llm_client.generate_response(prompt)

class Orchestrator:
    """
    The Main Coordinator (Custom Framework).
    Manages the workflow: Query -> Resolution -> Extraction -> Validation -> Response.
    Implements a retry loop for robust error handling.
    """
    def __init__(self, data_path):
        self.llm_client = LLMClient()
        self.data_loader = DataLoader(data_path)
        self.data_loader.load_data()
        
        self.query_agent = QueryResolutionAgent("QueryResolver", self.llm_client)
        self.extraction_agent = DataExtractionAgent(self.data_loader)
        self.validation_agent = ValidationAgent()
        self.response_agent = ResponseAgent("Responder", self.llm_client)

    def process_query(self, user_query: str):
        # 1. Resolve Query
        schema_info = self.data_loader.get_schema_info()
        sql_query = self.query_agent.resolve(user_query, schema_info)
        
        # 2. Extract Data with Retry/Self-Correction
        max_retries = 3
        data = None
        last_error = None
        
        for attempt in range(max_retries):
            try:
                data = self.extraction_agent.extract(sql_query)
                break # Success
            except Exception as e:
                last_error = str(e)
                print(f"Attempt {attempt+1} failed: {last_error}")
                # Try to fix the query
                if attempt < max_retries - 1:
                    sql_query = self.query_agent.fix_query(user_query, schema_info, sql_query, last_error)
        
        if data is None:
            return f"I couldn't answer that after {max_retries} attempts. Error: {last_error}"

        # 3. Validate
        if not self.validation_agent.validate(data):
            return "No data found matching your query."

        # 4. Generate Response
        response = self.response_agent.summarize(user_query, data, sql_query)
        return response

    def generate_summary(self):
        """Generates a comprehensive summary of the dataset."""
        queries = {
            "Total Sales": "SELECT SUM(Amount) FROM sales_data",
            "Sales by Year": "SELECT Year, SUM(Amount) FROM sales_data GROUP BY Year ORDER BY Year",
            "Top 5 Categories": "SELECT Category, SUM(Amount) FROM sales_data GROUP BY Category ORDER BY 2 DESC LIMIT 5",
            "Sales by Source": "SELECT Source, SUM(Amount) FROM sales_data GROUP BY Source"
        }
        
        results = {}
        for title, sql in queries.items():
            try:
                results[title] = self.extraction_agent.extract(sql)
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
        return self.llm_client.generate_response(prompt)

    def get_visualization_data(self):
        """Fetches data specifically for visualization."""
        queries = {
            "Sales by Year": "SELECT Year, SUM(Amount) as Total_Sales FROM sales_data GROUP BY Year ORDER BY Year",
            "Top 10 Categories": "SELECT Category, SUM(Amount) as Total_Sales FROM sales_data GROUP BY Category ORDER BY Total_Sales DESC LIMIT 10",
            "Sales by Source": "SELECT Source, SUM(Amount) as Total_Sales FROM sales_data GROUP BY Source"
        }
        
        results = {}
        for title, sql in queries.items():
            try:
                # Use extraction agent to get DataFrame directly
                df = self.extraction_agent.extract(sql)
                if isinstance(df, pd.DataFrame) and not df.empty:
                    # Set index for better plotting in Streamlit
                    if "Year" in df.columns:
                        df.set_index("Year", inplace=True)
                    elif "Category" in df.columns:
                        df.set_index("Category", inplace=True)
                    elif "Source" in df.columns:
                        df.set_index("Source", inplace=True)
                    results[title] = df
            except Exception as e:
                print(f"Error fetching visualization data for {title}: {e}")
        
        return results

if __name__ == "__main__":
    # Test run
    orchestrator = Orchestrator("data/Amazon Sale Report.csv")
    print(orchestrator.process_query("What is the total sales amount?"))
