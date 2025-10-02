from typing import Optional, TypedDict, Annotated, Sequence, Dict,List
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class RecommenderState(TypedDict):
    ''''''
    messages: Annotated[Sequence[BaseException],add_messages]
    user_query: str
    matches_metadata: Optional[List[Dict]]
    