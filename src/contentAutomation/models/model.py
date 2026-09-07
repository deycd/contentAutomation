from langchain_groq import ChatGroq
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
groq_client = Groq()
llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.2)
