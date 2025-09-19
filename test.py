import ollama

ollama.pull('gemma3:1b')

ollama_stream = ollama.chat(
            model="gemma3:1b",
            messages="Hi",
            stream=True,
        )

