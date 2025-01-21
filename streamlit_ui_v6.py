from sports_agent_v2 import SportsDataAgent
from langchain_core.messages import ToolMessage, AIMessage
import streamlit as st
import sqlparse
import re
import streamlit_authenticator as stauth


class StreamlitUI:
    def __init__(self, agent: SportsDataAgent):
        self.agent = agent
        if "messages" not in st.session_state:
            st.session_state.messages = []
        self.authenticator = stauth.Authenticate(
            st.secrets["credentials"].to_dict(),
            st.secrets["cookie"]["name"],
            st.secrets["cookie"]["key"],
            st.secrets["cookie"]["expiry_days"],
        )

    def display_sidebar(self):
        tables = self.agent.available_tables
        with st.sidebar:
            st.header(f'Welcome *{st.session_state["name"]}*')
            st.write("Available Tables")

            if tables:
                for table in tables:
                    st.write(f"- {table}")
            else:
                st.write("No tables available.")

            self.authenticator.logout()

    def render_message(self, role: str, content: str, message_type: str = "final"):
        """
        Render a message in the appropriate style based on its type.
        Parameters:
            role (str): Role of the message sender ('user', 'assistant', etc.).
            content (str): Content of the message.
            message_type (str): Type of the message ('final', 'tool_call', 'tool_output').
        """
        show_thought_process = st.session_state.get("show_thought_process", True)

        if message_type in ["tool_call", "tool_output"] and not show_thought_process:
            # Skip rendering thought process messages if hidden
            return

        if message_type == "tool_call":
            with st.expander("Thought Process: Tool Call", expanded=False, icon="🤔"):
                st.markdown(content)
        elif message_type == "tool_output":
            with st.expander("Thought Process: Tool Output", expanded=False, icon="💡"):
                st.markdown(content)
        else:  # Final message
            with st.chat_message(role):
                st.write(content)

    def append_and_display_message(
        self, role: str, content: str, message_type: str = "final"
    ):
        """
        Append a new message to the chat history and display it.
        """
        # Append the message to the chat history
        st.session_state.messages.append(
            {"role": role, "content": content, "type": message_type}
        )

        # Use the helper method to render the message
        self.render_message(role, content, message_type)

    def display_chat_history(self):
        """
        Replay the entire chat history with appropriate display logic for each message type.
        """
        show_thought_process = st.session_state.get("show_thought_process", True)

        for message in st.session_state.messages:
            role = message["role"]
            content = message["content"]
            message_type = message.get(
                "type", "final"
            )  # Default to 'final' if type is not set

            if (
                message_type in ["tool_call", "tool_output"]
                and not show_thought_process
            ):
                # Skip thought process messages if hidden
                continue

            self.render_message(role, content, message_type)

    def format_sql_query(self, query: str) -> str:
        """
        Format a SQL query string using sqlparse to improve readability.
        Parameters:
            query (str): The SQL query to format.
        Returns:
            str: The formatted SQL query, or the raw query if formatting fails.
        """
        try:
            # Check if the query starts and ends with a code block
            match = re.match(r"```(.*?)\n(.*?)```", query, re.DOTALL)
            if match:
                # If it's wrapped in a code block, strip the markers
                query = match.group(2).strip()

            # Attempt to format the SQL query using sqlparse
            formatted_query = sqlparse.format(
                query, reindent=True, keyword_case="upper"
            )
            return f"```sql\n{formatted_query}\n```"
        except Exception:
            # Fallback to raw query if formatting fails
            return f"```sql\n{query}\n```"

    def process_agent_response(self, user_input: str, config: dict):
        """
        Process the agent's response and update the chat history.
        """
        try:

            for event in self.agent.graph.stream(
                {"messages": [("user", user_input)]},
                config,
                stream_mode="values",
            ):
                message = event["messages"][-1]

                if isinstance(message, AIMessage) and message.tool_calls:
                    # Handle tool calls in AIMessage
                    for tool_call in message.tool_calls:
                        tool_name = tool_call.get("name", "Unknown Tool")
                        tool_args = tool_call.get("args", {})

                        # Extract SQL query and format
                        sql_query = tool_args.get("query")
                        if sql_query:
                            tool_call_message = f"**Tool Called**: `{tool_name}`\n\n**Arguments:**\n{self.format_sql_query(sql_query)}"
                        else:
                            # Fallback for non-SQL or unstructured arguments
                            tool_call_message = f"**Tool Called**: `{tool_name}`\n\n**Arguments:** `{tool_args}`"

                        # Append and display tool call details
                        self.append_and_display_message(
                            "assistant", tool_call_message, message_type="tool_call"
                        )

                elif isinstance(message, ToolMessage):
                    # Handle tool output (always formatted as SQL)
                    tool_output_message = (
                        f"**Tool Output:**\n\n{self.format_sql_query(message.content)}"
                    )

                    # Append and display tool output
                    self.append_and_display_message(
                        "assistant", tool_output_message, message_type="tool_output"
                    )

                elif isinstance(message, AIMessage):
                    # Final AI response (no tool calls)
                    self.append_and_display_message(
                        "assistant", message.content, message_type="final"
                    )

        except Exception as e:
            st.error(f"An error occurred while processing the agent's response: {e}")

    def handle_user_input(self, user_input: str):
        """
        Handle the user's input and process the response from the agent.
        """
        config = {"configurable": {"thread_id": "thread-demo"}}
        self.append_and_display_message("user", user_input)
        self.process_agent_response(user_input, config)

    def run(self):
        """
        Main method to render the Streamlit app.
        """

        try:
            self.authenticator.login()
        except Exception as e:
            st.error(e)

        if st.session_state["authentication_status"]:

            self.display_sidebar()
            st.title("🏆Sports Data Agent🏆")
            st.toggle("Show thought process", value=True, key="show_thought_process")
            self.display_chat_history()

            if user_input := st.chat_input(
                placeholder="Ask a question about sports data..."
            ):
                self.handle_user_input(user_input)
        elif st.session_state["authentication_status"] is False:
            st.error("Username/password is incorrect")
        elif st.session_state["authentication_status"] is None:
            st.warning("Please enter your username and password")
