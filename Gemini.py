
import google.generativeai as genai

class GeminiLLM():
    def __init__(self):
        super().__init__()
        genai.configure(api_key='INSERT KEY HERE')
        self.model = genai.GenerativeModel('gemini-pro')
        self.safety_settings = [
            {
                "category": "HARM_CATEGORY_DANGEROUS",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE",
            },
        ]

    def send_prompt(self, prompt, temperature=0.5):
        while True:
            try:

                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig( temperature=temperature
                    ),
                    safety_settings=self.safety_settings
                )
                break
            except Exception as e:
                print(e)
                print('retrying... hit limit or error')
                continue
        return response.text

