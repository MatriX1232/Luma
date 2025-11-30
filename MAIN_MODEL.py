from ollama import chat, ChatResponse


class MAIN_MODEL:
    def __init__(self, model_name="llama3.2", temperature=0.7, max_tokens=512):
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.stream = None


    def generate_response(self, prompt):
        response: ChatResponse = chat(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )
        
        for chunk in response:
            yield chunk['message']['content']


if __name__ == "__main__":
    model = MAIN_MODEL(model_name="llama3.2", temperature=0.5, max_tokens=256)
    prompt = "Explain the theory of relativity in simple terms."
    response = model.generate_response(prompt)
    print("Response from model:")
    for chunk in response:
        print(chunk, end='', flush=True)