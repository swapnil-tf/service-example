class Bot:
    def __init__(self, bot_name: str):
        self.bot_name: str = bot_name

    def hello(self, your_name: str):
        return f"Hello {your_name}. I am {self.bot_name}."
