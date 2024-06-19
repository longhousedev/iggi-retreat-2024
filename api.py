from openai import OpenAI
import json
import time


class API:
    def __init__(self, players : list[dict], config_path: str = "config.json") -> None:
        self.client = OpenAI()

        with open(config_path) as f:
            self.config = json.load(f)
        self.model_name = self.config.get("model", "gpt-3.5-turbo")
        print("Using model:", self.model_name)
        print("Players:", [player["name"] for player in players])

        # initialize chat history
        self.players_chats = {}
        for player in players:
            if player["role"] == "moderator":
                self.players_chats[player["name"]] = [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant and master storyteller, you craft stories that are engaging and deeply meaningful.",
                    },
                    {"role": "user", "content": self.config[""]},
                ]
            elif player["role"] == "player":
                self.players_chats[player["name"]] = [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant and master storyteller, you craft stories that are engaging and deeply meaningful.",
                    },
                    {"role": "user", "content": self.config["initial_player_prompt"]},
                ]

    def _send_prompt(self, messages, temperature: float = 0.5):
        while True:
            try:
                chat_completion = self.client.chat.completions.create(
                    messages=messages,
                    model=self.model_name,
                    temperature=temperature,
                )
                return chat_completion.choices[0].message.content
            except Exception as e:
                print(e)
                print("retrying... hit limit or error")
                continue


if __name__ == "__main__":
    # gm should be first
    players = [
        {"name": "Jon", "role": "gm"},
        {"name": "Peter", "role": "player"},
    ]
    api = API(players)

    # 4 turns
    for i in range(4):
        for player in players:
            time.sleep(1)
            player_name = player["name"]
            player_role = player["role"]  # player or gm
            # gpt_role = "user" if player_role == "player" else "assistant"
            gpt_response = api._send_prompt(api.players_chats[player_name])
            api.players_chats[player_name].append(
                {"role": "assistant", "content": gpt_response}
            )
            for player in players:
                if player["name"] != player_name:
                    api.players_chats[player["name"]].append(
                        {
                            "role": "user",
                            "content": f"{player_name} says: {gpt_response}",
                        }
                    )

            if player_role == "gm":
                print(f"GM ({player_name}):", gpt_response)
                # Send this response to all other players

            elif player_role == "player":
                print(f"Player ({player_name}):", gpt_response)
                # Send this response to all other players
            else:
                raise ValueError("Invalid player role")

            # log messages to text file
            with open(f"message_{player_name}.txt", "w") as f:
                for message in api.players_chats[player_name]:
                    # just write the content
                    f.write(f"{message['role']}: {message['content']}\n")
