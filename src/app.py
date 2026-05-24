from dotenv import load_dotenv

load_dotenv()

from chatbot import BankingChatbot  # noqa: E402
from log_setup import setup_logging  # noqa: E402

setup_logging()


def main() -> None:
    print("Mehmet Bank Assistant — type 'exit' or 'quit' to stop, 'reset' to clear history.\n")
    bot = BankingChatbot(data_dir="data/")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        if user_input.lower() == "reset":
            bot.reset()
            print("Conversation history cleared.\n")
            continue

        response = bot.chat(user_input)
        print(f"\nAssistant: {response}\n")


if __name__ == "__main__":
    main()
