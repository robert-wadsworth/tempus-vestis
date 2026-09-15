from dotenv import load_dotenv

# Loaded once for the whole test session so eval tests (tests/evals/) can reach
# OPENAI_API_KEY the same way main.py does, without every test file needing its
# own load_dotenv() call.
load_dotenv()
