import subprocess

def list_ollama_models():
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            print("❌ Failed to list Ollama models")
            print(result.stderr)
            return

        print("🧠 Available Ollama models:\n")
        print(result.stdout)

    except FileNotFoundError:
        print("❌ Ollama is not installed or not in PATH.")
        print("👉 Install from: https://ollama.com")

    except Exception as e:
        print("❌ Unexpected error:", e)


if __name__ == "__main__":
    list_ollama_models()
