from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import InMemorySaver
from backend.app.product_recommender_agent import product_recommender_agent
from backend.app.state import RecommenderState
from backend.mongodb.create_collection import collection
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage

analyze_data_graph = StateGraph(RecommenderState)

analyze_data_graph.add_node("data_analyzer",product_recommender_agent)

analyze_data_graph.add_edge(START, "data_analyzer")

analyze_data_graph.add_edge("data_analyzer", END)

checkpointer = InMemorySaver()
analyze_data_graph = analyze_data_graph.compile(checkpointer=checkpointer)

current_idx = -1

id_ = "1234"
if __name__ == "__main__":
    # Example usage

    # new_conversation = {
    #     "user_identity": "sarthak",
    #     "conversation_id": id_,  # unique for each session
    #     "messages": [],
    #     "created_at": datetime.utcnow(),
    #     "updated_at": datetime.utcnow()
    # }
    
    # if collection.count_documents({"conversation_id": id_}) == 0:
    #     collection.insert_one(new_conversation)
    
    # for doc in collection.find_one({"conversation_id": id_}):
    #     print(doc)
    config = {"configurable": {"thread_id": "1"}}
    input = {"messages": [], "user_query": "looking for blue shirts with nike logo"}
    out = analyze_data_graph.invoke(input, config)
    # for msg in out['messages']:
    #     if isinstance(msg, HumanMessage):
    #         collection.update_one({"user_identity": "sarthak"},{"$push":{"messages":{"role":"user","content":msg.content}}})
    #     elif isinstance(msg, AIMessage):
    #         collection.update_one({"user_identity": "sarthak"},{"$push":{"messages":{"role":"ai","content":msg.content}}})