import pandas as pd
import duckdb
import os

class DataLoader:
    """
    Handles the ingestion, cleaning, and querying of data.
    Uses DuckDB as an in-memory OLAP engine for high-performance querying of CSV files.
    """
    def __init__(self, data_paths):
        # Ensure data_paths is a list
        if isinstance(data_paths, str):
            self.data_paths = [data_paths]
        else:
            self.data_paths = data_paths
        # Initialize DuckDB in-memory database
        self.con = duckdb.connect(database=':memory:')
        
    def load_data(self):
        """
        Core ETL Function:
        1. Iterates through provided file paths.
        2. Identifies file type based on column signatures (Amazon vs International vs Stock).
        3. Applies specific transformations (cleaning, renaming).
        4. Merges similar data (Sales) into a unified 'sales_data' table.
        5. Registers tables in DuckDB.
        """
        sales_dfs = []
        stock_dfs = []
        pricing_dfs = []
        
        for path in self.data_paths:
            if not os.path.exists(path):
                print(f"Warning: File not found: {path}")
                continue
                
            try:
                filename = os.path.basename(path)
                df = pd.read_csv(path, low_memory=False)
                
                # Remove duplicate columns if any
                if not df.columns.is_unique:
                    df = df.loc[:, ~df.columns.duplicated()]
                
                # Identify file type
                if 'Order ID' in df.columns and 'Fulfilment' in df.columns:
                    # Amazon Sales Report
                    df = self._transform_amazon(df)
                    sales_dfs.append(df)
                    print(f"Loaded Sales data from {filename}")
                elif 'GROSS AMT' in df.columns and 'PCS' in df.columns:
                    # International Sales Report
                    df = self._transform_international(df)
                    sales_dfs.append(df)
                    print(f"Loaded Sales data from {filename}")
                elif 'Stock' in df.columns and 'SKU Code' in df.columns:
                    # Stock Data
                    df = self._transform_stock(df)
                    stock_dfs.append(df)
                    print(f"Loaded Stock data from {filename}")
                elif 'Amazon MRP' in df.columns and 'TP' in df.columns:
                    # Pricing Data
                    df = self._transform_pricing(df)
                    pricing_dfs.append(df)
                    print(f"Loaded Pricing data from {filename}")
                else:
                    print(f"Skipping {filename}: Unknown format")
                    continue
                
            except Exception as e:
                print(f"Error loading data from {path}: {e}")
        
        # Register Sales Data
        if sales_dfs:
            try:
                final_sales = pd.concat(sales_dfs, ignore_index=True)
                final_sales['Amount'] = pd.to_numeric(final_sales['Amount'], errors='coerce').fillna(0.0)
                final_sales['Qty'] = pd.to_numeric(final_sales['Qty'], errors='coerce').fillna(0)
                
                # Time Dimensions
                final_sales['Year'] = final_sales['Date'].dt.year
                final_sales['Month'] = final_sales['Date'].dt.month
                final_sales['Quarter'] = final_sales['Date'].dt.quarter
                final_sales['Month_Name'] = final_sales['Date'].dt.month_name()
                
                self.con.register('sales_data', final_sales)
                print(f"Registered 'sales_data' with {len(final_sales)} rows.")
            except Exception as e:
                print(f"Error registering sales_data: {e}")

        # Register Stock Data
        if stock_dfs:
            try:
                final_stock = pd.concat(stock_dfs, ignore_index=True)
                self.con.register('stock_data', final_stock)
                print(f"Registered 'stock_data' with {len(final_stock)} rows.")
            except Exception as e:
                print(f"Error registering stock_data: {e}")

        # Register Pricing Data
        if pricing_dfs:
            try:
                final_pricing = pd.concat(pricing_dfs, ignore_index=True)
                self.con.register('pricing_data', final_pricing)
                print(f"Registered 'pricing_data' with {len(final_pricing)} rows.")
            except Exception as e:
                print(f"Error registering pricing_data: {e}")

    def _transform_stock(self, df):
        """Cleans Stock data."""
        # Rename for consistency
        df = df.rename(columns={
            'SKU Code': 'SKU',
            'Design No.': 'Style_ID'
        })
        # Ensure Stock is numeric
        df['Stock'] = pd.to_numeric(df['Stock'], errors='coerce').fillna(0)
        return df

    def _transform_pricing(self, df):
        """Cleans Pricing data."""
        # Rename
        df = df.rename(columns={
            'Sku': 'SKU',
            'Style Id': 'Style_ID'
        })
        # Clean numerics
        numeric_cols = ['TP', 'Amazon MRP', 'Flipkart MRP', 'Ajio MRP']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df

    def _transform_amazon(self, df):
        """Cleans and normalizes Amazon Sales data."""
        # Date: 04-30-22 (MM-DD-YY)
        df['Date'] = pd.to_datetime(df['Date'], format='%m-%d-%y', errors='coerce')
        
        # Amount
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0.0)
        
        # Rename for consistency
        df = df.rename(columns={
            'Order ID': 'Order_ID',
            'ship-city': 'City', 
            'ship-state': 'State', 
            'ship-country': 'Country',
            'Fulfilment': 'Channel' # Mapping Fulfilment to Channel for broad categorization
        })
        
        df['Source'] = 'Amazon'
        
        # Remove duplicate columns if any (e.g. if City existed before rename)
        if not df.columns.is_unique:
            df = df.loc[:, ~df.columns.duplicated()]
        
        # Select common columns
        cols = ['Date', 'Order_ID', 'SKU', 'Qty', 'Amount', 'City', 'State', 'Country', 'Category', 'Size', 'Status', 'Source']
        # Ensure all cols exist
        for col in cols:
            if col not in df.columns:
                df[col] = None
                
        return df[cols].copy()

    def _transform_international(self, df):
        """Cleans and normalizes International Sales data."""
        # Date: 06-05-21 (DD-MM-YY usually, checking sample)
        # Sample: 06-05-21 -> Jun-21. So likely DD-MM-YY or MM-DD-YY. 
        # Given "International", DD-MM-YY is more common, but let's infer.
        df['Date'] = pd.to_datetime(df['DATE'], format='%m-%d-%y', errors='coerce')
        
        # Rename
        df = df.rename(columns={
            'PCS': 'Qty', 
            'GROSS AMT': 'Amount',
            'Style': 'SKU' # Mapping Style to SKU as it seems to be the product identifier here
        })
        
        # Ensure Amount is numeric
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0.0)
        
        df['Source'] = 'International'
        
        # Remove duplicate columns if any
        if not df.columns.is_unique:
            df = df.loc[:, ~df.columns.duplicated()]
        df['Country'] = 'International' # Default if not specified
        df['City'] = None
        df['State'] = None
        df['Order_ID'] = df.index.astype(str) # No Order ID in sample, using index
        df['Category'] = None # Not in sample
        df['Size'] = df['Size']
        df['Status'] = 'Delivered' # Assumption for completed sales
        
        # Select common columns
        cols = ['Date', 'Order_ID', 'SKU', 'Qty', 'Amount', 'City', 'State', 'Country', 'Category', 'Size', 'Status', 'Source']
        
        # Ensure only these columns are returned and they are unique
        return df[cols].copy()

    def query(self, sql_query: str):
        """
        Executes a SQL query against the DuckDB instance.
        Returns the result as a Pandas DataFrame.
        """
        try:
            return self.con.execute(sql_query).fetchdf()
        except Exception as e:
            print(f"Query error: {e}")
            raise

    def get_schema_info(self):
        """
        Introspection:
        Retrieves the schema (table names, column names, data types) of all registered tables.
        This string is injected into the LLM prompt to enable context-aware SQL generation.
        """
        try:
            tables = self.con.execute("SHOW TABLES").fetchdf()
            schema_info = []
            
            for _, row in tables.iterrows():
                table_name = row['name']
                schema_df = self.con.execute(f"DESCRIBE {table_name}").fetchdf()
                columns = []
                for _, col_row in schema_df.iterrows():
                    columns.append(f"{col_row['column_name']} ({col_row['column_type']})")
                schema_info.append(f"Table '{table_name}': " + ", ".join(columns))
                
            return "\n\n".join(schema_info)
        except Exception as e:
            return f"Error getting schema: {e}"

if __name__ == "__main__":
    # Test run
    loader = DataLoader("data/Amazon Sale Report.csv")
    loader.load_data()
    print(loader.query("SELECT count(*) FROM sales_data"))
    print(loader.query("SELECT sum(Amount) FROM sales_data"))
