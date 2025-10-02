from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool
from langchain_core.output_parsers import StrOutputParser
from langchain.load import dumps, loads
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.app.state import RecommenderState
import os 
from Config.config import Config
from backend.utils.logger import get_logger
from backend.app.prompt import rag_prompt
from dotenv import load_dotenv
from backend.database.setup_db import pc, index_name
from langchain_huggingface import HuggingFaceEmbeddings

index = pc.Index(index_name)
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-base-en-v1.5")
load_dotenv()

logger = get_logger(__name__)

os.environ["GOOGLE_API_KEY"] = Config.GOOGLE_API_KEY

def product_recommender_agent(state : RecommenderState) -> RecommenderState:

    llm = ChatGoogleGenerativeAI(model = "gemini-2.0-flash")
    query_vector = embeddings.embed_query(state["user_query"])
    results = index.query(
        vector = query_vector,
        top_k = 3,
        include_values = False,
        include_metadata = True
    )

    # ✅ convert ScoredVector -> dict
    state["matches_metadata"] = [
        {"metadata": match.metadata}
        for match in results['matches']
    ]

    excluded = {"url", "asin", "stars"}
    each_match_string = []
    for match in results['matches']:
        print(match)
        big_string = " ".join([f"{k}:{v}" for k, v in match['metadata'].items() if k not in excluded])
        each_match_string.append(big_string)

    context_str = "\n\n".join(each_match_string)

    chat_history = state['messages']
    state['messages'].append(HumanMessage(content = state["user_query"]))
    updated_prompt = rag_prompt.invoke({"user_query":state["user_query"], "chat_history":chat_history, "context":[context_str]})
    response = llm.invoke(updated_prompt)
    state["messages"].append(AIMessage(content=response.content))
    # parser = StrOutputParser()
    # output_response = parser.parse(response)
    return state







