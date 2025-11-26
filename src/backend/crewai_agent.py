import os
from crewai import Agent, Task, Crew, Process, LLM
from src.backend.data_loader import DataLoader
import pandas as pd

from crewai.tools import BaseTool

# Define a custom tool for the agents to use
class DatabaseTool(BaseTool):
    name: str = "Execute SQL"
    description: str = "Executes a DuckDB SQL query and returns the results as a string."
    data_loader: DataLoader = None

    def _run(self, sql_query: str):
        """Executes a DuckDB SQL query and returns the results as a string."""
        try:
            # Clean SQL
            sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
            df = self.data_loader.query(sql_query)
            if df.empty:
                return "Query executed successfully but returned no data."
            return df.to_string()
        except Exception as e:
            return f"Error executing SQL: {e}"

class CrewAIAgent:
    def __init__(self, data_paths):
        self.data_loader = DataLoader(data_paths)
        self.data_loader.load_data()
        
        # Initialize LLM
        # CrewAI uses LiteLLM under the hood. 
        # We use the 'gemini/' prefix and the model name.
        api_key = os.getenv("GOOGLE_API_KEY")
        self.llm = LLM(model="gemini/gemini-flash-latest", api_key=api_key)
        
        # Initialize Tools
        self.db_tool = DatabaseTool(data_loader=self.data_loader)
        
        # --- Define Agents ---
        
        # 1. Language to Query Resolution Agent
        self.query_resolution_agent = Agent(
            role='Query Resolution Specialist',
            goal='Translate natural language questions into syntactically correct DuckDB SQL queries.',
            backstory='You are an expert in SQL dialects and database schemas. You do NOT execute queries, you only write them.',
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

        # 2. Data Extraction Agent
        self.data_extraction_agent = Agent(
            role='Database Administrator',
            goal='Execute the provided SQL query and retrieve the raw data.',
            backstory='You have access to the database. You execute the exact SQL provided to you.',
            tools=[self.db_tool],
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

        # 3. Validation Agent
        self.validation_agent = Agent(
            role='Data Validator',
            goal='Validate that the retrieved data is not empty and contains meaningful results.',
            backstory='You check the quality of the data. If the data is "No data" or empty, you flag it.',
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )
        
        # 4. Response Agent (Analyst)
        self.response_agent = Agent(
            role='Retail Data Analyst',
            goal='Synthesize the validated data into a clear, human-readable answer.',
            backstory='You answer the user question based ONLY on the validated data provided.',
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

    def process_query(self, user_query: str):
        schema = self.data_loader.get_schema_info()
        
        # --- Define Tasks ---
        
        # Task 1: Resolve (Language -> SQL)
        task_resolve = Task(
            description=f"""
            Translate the user's question into a DuckDB SQL query.
            User Question: "{user_query}"
            Database Schema: {schema}
            Return ONLY the SQL query, no markdown.
            """,
            expected_output="A valid DuckDB SQL query string.",
            agent=self.query_resolution_agent
        )
        
        # Task 2: Extract (SQL -> Data)
        task_extract = Task(
            description="Execute the SQL query provided by the Query Resolution Specialist using the 'Execute SQL' tool.",
            expected_output="The raw data returned from the database.",
            agent=self.data_extraction_agent,
            context=[task_resolve]
        )
        
        # Task 3: Validate (Data -> Validated Data)
        task_validate = Task(
            description="Check if the data provided by the Database Administrator is empty or contains an error message. If it is valid, pass it through.",
            expected_output="The validated data or a specific error message.",
            agent=self.validation_agent,
            context=[task_extract]
        )
        
        # Task 4: Respond (Validated Data -> Answer)
        task_respond = Task(
            description=f"Answer the user's original question: '{user_query}' based on the validated data.",
            expected_output="A concise answer to the user.",
            agent=self.response_agent,
            context=[task_validate]
        )
        
        crew = Crew(
            agents=[self.query_resolution_agent, self.data_extraction_agent, self.validation_agent, self.response_agent],
            tasks=[task_resolve, task_extract, task_validate, task_respond],
            process=Process.sequential,
            verbose=True
        )
        
        result = crew.kickoff()
        return result

    def generate_summary(self):
        # Re-using the logic from other agents for consistency
        queries = {
            "Total Sales": "SELECT SUM(Amount) FROM sales_data",
            "Sales by Year": "SELECT Year, SUM(Amount) FROM sales_data GROUP BY Year ORDER BY Year",
            "Top 5 Categories": "SELECT Category, SUM(Amount) FROM sales_data GROUP BY Category ORDER BY 2 DESC LIMIT 5",
            "Sales by Source": "SELECT Source, SUM(Amount) FROM sales_data GROUP BY Source"
        }
        
        results = {}
        for title, sql in queries.items():
            try:
                df = self.data_loader.query(sql)
                results[title] = df.to_string() if not df.empty else "No data"
            except Exception as e:
                results[title] = f"Error: {e}"
                
        task_summary = Task(
            description=f"""
            You are a senior business analyst. Generate a concise, human-readable executive summary of the sales performance based on the following data:
            
            {results}
            
            Focus on:
            1. Total Sales and growth.
            2. Top performing categories.
            3. Any significant trends.
            
            Format the output with clear headings and bullet points.
            """,
            expected_output="An executive summary report.",
            agent=self.response_agent
        )
        
        crew = Crew(
            agents=[self.response_agent],
            tasks=[task_summary],
            verbose=True
        )
        
        return crew.kickoff()
