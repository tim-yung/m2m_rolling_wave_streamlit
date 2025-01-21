from dotenv import load_dotenv
import pandas as pd
from sqlalchemy import create_engine
import os

from langchain import hub
from langchain_openai import ChatOpenAI
from langchain_core.messages import trim_messages
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import MessagesState, StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition


class SportsDataAgent:
    def __init__(self, db_path: str, data_folder: str, model_name: str):
        """
        Initialize the SportsDataAgent class.
        """
        # Load environment variables
        # load_dotenv()

        # Create database engine
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.db = SQLDatabase(engine=self.engine)

        # Load CSVs into the database
        self.load_csvs_into_database(data_folder)

        # Log available tables
        self.available_tables = self.log_available_tables()

        # Initialize LLM and tools
        self.llm = ChatOpenAI(model=model_name, temperature=0)
        self.toolkit = SQLDatabaseToolkit(db=self.db, llm=self.llm)
        self.tools = self.toolkit.get_tools()

        # Bind tools with LLM
        self.llm_with_tools = self.llm.bind_tools(
            self.tools, parallel_tool_calls=False
        )  # disabled parallel tool calling as it is error-prone

        # Build the graph
        self.graph = self.build_graph()

    def build_graph(self):
        """
        Build the graph for the SportsDataAgent.
        """

        def call_model(state: MessagesState):
            prompt_template = hub.pull("langchain-ai/sql-agent-system-prompt")
            system_message = prompt_template.format(dialect="SQLite", top_k=5)
            messages = trim_messages(
                state["messages"],
                max_tokens=4000,  # limit token usage
                strategy="last",
                token_counter=self.llm_with_tools,
                start_on="human",
                end_on=("human", "tool"),
                include_system=True,
                allow_partial=False,
            )

            return {
                "messages": [self.llm_with_tools.invoke([system_message] + messages)]
            }

        workflow = StateGraph(MessagesState)
        workflow.add_node("chatbot", call_model)
        workflow.add_node("tools", ToolNode(self.tools))
        workflow.add_edge(START, "chatbot")
        workflow.add_conditional_edges("chatbot", tools_condition)
        workflow.add_edge("tools", "chatbot")
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)

    def load_csvs_into_database(self, data_folder: str):
        """
        Load all CSV files in the given folder into the database as separate tables.
        """
        try:
            for file_name in os.listdir(data_folder):
                if file_name.endswith(".csv"):
                    table_name = (
                        os.path.splitext(file_name)[0].replace(" ", "_").lower()
                    )
                    file_path = os.path.join(data_folder, file_name)
                    df = pd.read_csv(file_path)
                    df.to_sql(table_name, self.engine, index=False, if_exists="replace")
        except Exception as e:
            raise RuntimeError(f"Error loading CSVs: {e}")

    def log_available_tables(self):
        """
        Log all available tables in the database for debugging purposes.
        """
        return self.db.get_usable_table_names()
