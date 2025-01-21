from streamlit_ui_v6 import StreamlitUI
from sports_agent_v2 import SportsDataAgent
import streamlit as st


def main():
    db_path = "sports_data.db"
    data_folder = "1_data"
    model_name = "gpt-4o-mini"

    if "sports_agent" not in st.session_state:
        st.session_state.sports_agent = SportsDataAgent(
            db_path, data_folder, model_name
        )

    ui = StreamlitUI(st.session_state.sports_agent)
    ui.run()


if __name__ == "__main__":
    main()
