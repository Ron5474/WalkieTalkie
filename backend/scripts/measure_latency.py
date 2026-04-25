"""Quick latency probe: same chat turn twice, prints elapsed seconds from agent_runner."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.chdir(os.path.dirname(os.path.dirname(__file__)))

from langchain_core.messages import HumanMessage

from agent_runner import run_chat_turn


def main():
    text = "I'm near Embarcadero — one walking story and a cheap eat under my budget."
    human = HumanMessage(
        content=(
            "Backend context: user_id=student_1; GPS=Lat: 37.7955, Long: -122.3937; focus_city=San Francisco.\n\n"
            + text
        )
    )
    for i in range(2):
        _, elapsed = run_chat_turn(
            [human],
            tier="small",
            user_id="student_1",
            city="San Francisco",
            latitude=37.7955,
            longitude=-122.3937,
        )
        print(f"run {i+1}: {elapsed:.3f}s")


if __name__ == "__main__":
    main()
