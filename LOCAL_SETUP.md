# Local Setup Guide for Retail Insights Assistant

This guide provides step-by-step instructions to set up and run the Retail Insights Assistant locally on your machine.

## Prerequisites

Before you begin, ensure you have the following installed:

*   **Python 3.10 or higher**: [Download Python](https://www.python.org/downloads/)
*   **Git**: [Download Git](https://git-scm.com/downloads)
*   **VS Code (Optional)**: Recommended for code editing.

## Installation

### 1. Clone the Repository

Open your terminal or command prompt and run the following command to clone the repository:

```bash
git clone https://github.com/6736-shafi/retail-insights-assistant.git
cd retail-insights-assistant
```

### 2. Create a Virtual Environment

It is best practice to use a virtual environment to manage dependencies. Run the following command:

**macOS / Linux:**
```bash
python3 -m venv venv
```

**Windows:**
```bash
python -m venv venv
```

### 3. Activate the Virtual Environment

Activate the virtual environment to isolate your project dependencies:

**macOS / Linux:**
```bash
source venv/bin/activate
```

**Windows:**
```bash
.\venv\Scripts\activate
```

_You should see `(venv)` appear at the beginning of your terminal line, indicating the virtual environment is active._

### 4. Install Dependencies

Install the required Python packages using `pip`:

```bash
pip install -r requirements.txt
```

## Configuration

### 1. Set up Environment Variables

The application requires API keys to function.

1.  Create a new file named `.env` in the root directory of the project.
2.  You can copy the template from `.env.example`:

    **macOS / Linux:**
    ```bash
    cp .env.example .env
    ```

    **Windows:**
    ```bash
    copy .env.example .env
    ```

3.  Open the `.env` file and add your Google Gemini API Key:

    ```env
    GOOGLE_API_KEY=your_actual_api_key_here
    ```

    *   If you don't have a key, get one from [Google AI Studio](https://aistudio.google.com/).

## Running the Application

Once everything is set up, you can start the application.

### 1. Start the Streamlit Interface

Run the following command from the root directory:

```bash
streamlit run src/ui/app.py
```

### 2. Access the App

The application should automatically open in your default web browser. If not, navigate to the URL shown in the terminal, usually:

`http://localhost:8501`

### 3. Using the App

1.  **Upload Data**: On the sidebar, look for the file upload section. You can upload CSV files containing your retail data (e.g., Sales Reports, Inventory).
2.  **Ask Questions**: In the main chat interface, type your questions about the data.
    *   *Example*: "What was the total revenue last month?"
    *   *Example*: "Show me the top selling products."
3.  **View Insights**: The assistant will process your query and display answers, charts, and insights based on the uploaded data.

## Troubleshooting

*   **"Module not found" error**: Ensure your virtual environment is activated (`(venv)` is visible) and you have run `pip install -r requirements.txt`.
*   **API Key errors**: Double-check that your `.env` file exists and contains the correct `GOOGLE_API_KEY`.
*   **Port already in use**: If `localhost:8501` is taken, Streamlit will automatically try the next available port (e.g., 8502). Check the terminal output for the correct URL.
