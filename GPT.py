from openai import OpenAI

class GPT():
    def __init__(self):
        super().__init__()
        self.model = OpenAI(
                    api_key="INSERT_KEY_HERE",
                )

    def send_prompt(self, prompt, temperature=0.5):
        while True:
            try:
                chat_completion = self.model.chat.completions.create(
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    model="gpt-4",
                    temperature=temperature
                )
                return chat_completion.choices[0].message.content
            except Exception as e:
                print(e)
                print('retrying... hit limit or error')
                continue


