from bot.app.bot_client import create_bot_app
from bot.app.settings import TOKEN


if __name__ == "__main__":
    app = create_bot_app()
    app.client.run(TOKEN)
