from fastapi import FastAPI, UploadFile, Form, Response, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
from typing import List, Dict, Optional
from pathlib import Path
from fastapi.exceptions import RequestValidationError
import pickle
from pydantic import BaseModel, Field, field_validator
from backend.mongodb.create_collection import collection
from datetime import datetime, timedelta
from backend.app.graph import analyze_data_graph
import requests
from langchain_core.messages import HumanMessage, AIMessage
from cachetools import TTLCache
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VerifyRequest(BaseModel):
    uuid: str = Field(..., description="the uuid for the user session")
    user_identity: str = Field(..., description="User name or email")

    @field_validator("user_identity")
    def check_valid_user_identity(cls, value):
        not_valid_chars = {
            '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/',
            ':', ';', '<', '=', '>', '?', '@', '[', '\\', ']', '^', '_', '`', '{', '|', 
            '}', '~', ' ', '\t', '\n', '\r', '\x0b', '\x0c'
        }

        if set(value) & not_valid_chars:
            raise ValueError("Invalid user name, don't use any special characters")
        elif len(value) > 15:
            raise ValueError("User detail too long keep it under 15 characters")
        
        return value

class ChatRequest(BaseModel):
    uuid: str
    user_query: str
    is_selected_products: Optional[bool] = False


app = FastAPI(title="Amazon Product Recommender")

# TTL Cache: max 1000 conversations, 1 hour expiration
app.state.cache_conversations = TTLCache(maxsize=1000, ttl=3600)

# Allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Create database indexes on startup"""
    try:
        collection.create_index("conversation_id", unique=True)
        collection.create_index("user_identity")
        collection.create_index([("user_identity", 1), ("created_at", -1)])
        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return a simple error JSON for easy consumption by frontend"""
    errors = {}
    for err in exc.errors():
        field = ".".join(str(loc) for loc in err["loc"] if loc != "body")
        errors.setdefault(field, []).append(err["msg"])
    return JSONResponse(status_code=422, content={"details": errors})


@app.post("/conversations/new")  # Changed from GET to POST
async def create_new_conversation(user_data: VerifyRequest):
    """Create a new conversation for a user"""
    conv_uuid = user_data.uuid
    user_identity = user_data.user_identity
    
    try:
        # Check if conversation already exists
        existing = collection.count_documents({"conversation_id": conv_uuid}, limit=1)
        
        if existing == 0:
            new_conversation = {
                "user_identity": user_identity,
                "conversation_id": conv_uuid,
                "messages": [],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            collection.insert_one(new_conversation)
            logger.info(f"Created new conversation: {conv_uuid} for user: {user_identity}")

        # Fetch user conversations with projection (only needed fields)
        user_docs = collection.find(
            {"user_identity": user_identity},
            {"conversation_id": 1, "messages": 1, "_id": 0}
        ).sort("created_at", -1)  # Most recent first
        
        user_conversations = {
            doc['conversation_id']: doc['messages'] 
            for doc in user_docs
        }

        # Update cache
        for conv_id, messages in user_conversations.items():
            app.state.cache_conversations[conv_id] = messages

        return {"conversation_history": user_conversations}
    
    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to create conversation")


@app.delete("/conversations/{conversation_id}")  # Changed from GET to DELETE
async def delete_conversation(conversation_id: str):
    """Delete a specific conversation"""
    try:
        result = collection.delete_one({"conversation_id": conversation_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Remove from cache
        app.state.cache_conversations.pop(conversation_id, None)
        
        logger.info(f"Deleted conversation: {conversation_id}")
        return {"message": "Conversation deleted successfully", "conversation_id": conversation_id}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete conversation")


@app.get("/conversations/{user_identity}")
async def get_user_conversations(user_identity: str, limit: int = 50):
    """Get all conversations for a user"""
    try:
        user_docs = collection.find(
            {"user_identity": user_identity},
            {"conversation_id": 1, "messages": 1, "created_at": 1, "_id": 0}
        ).sort("created_at", -1).limit(limit)
        
        conversations = {
            doc['conversation_id']: {
                "messages": doc['messages'],
                "created_at": doc.get('created_at')
            }
            for doc in user_docs
        }
        
        return {"conversations": conversations}
    
    except Exception as e:
        logger.error(f"Error fetching conversations: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch conversations")

    
@app.post("/chat")
async def chat_with_agent(chat_request: ChatRequest):
    """Handle chat interaction with the agent"""
    user_query = chat_request.user_query
    conv_uuid = chat_request.uuid
    is_selected_products = chat_request.is_selected_products    
    
    try:
        if not is_selected_products:
            # Get previous messages from cache or database
            prev_messages = app.state.cache_conversations.get(conv_uuid)
            
            if prev_messages is None:
                # Cache miss - fetch from database
                conversation = collection.find_one(
                    {"conversation_id": conv_uuid},
                    {"messages": 1, "_id": 0}
                )
                
                if not conversation:
                    raise HTTPException(status_code=404, detail="Conversation not found")
                
                prev_messages = conversation.get('messages', [])
                app.state.cache_conversations[conv_uuid] = prev_messages
            
            # Format messages efficiently
            formatted_messages = [
                HumanMessage(content=msg["content"]) if msg["role"] == "user"
                else AIMessage(content=msg["content"])
                for msg in prev_messages
                if msg["role"] in ["user", "ai"]
            ]
        else:
            formatted_messages = []
            
        
        # Invoke the graph
        config = {"configurable": {"thread_id": conv_uuid}}
        input_data = {"messages": formatted_messages, "user_query": user_query}
        out = analyze_data_graph.invoke(input_data, config)
        
        # Prepare messages for batch update
        messages_to_add = []
        cache_updates = []
        
        for msg in out['messages'][-2:]:
            if isinstance(msg, HumanMessage):
                msg_dict = {"role": "user", "content": msg.content}
                messages_to_add.append(msg_dict)
                cache_updates.append(msg_dict)
            elif isinstance(msg, AIMessage):
                msg_dict = {"role": "ai", "content": msg.content}
                messages_to_add.append(msg_dict)
                cache_updates.append(msg_dict)
        
        # Add metadata if present
        if len(out.get('matches_metadata', [])) > 0:
            metadata_msg = {"role": "metadata", "content": out['matches_metadata']}
            messages_to_add.append(metadata_msg)
            cache_updates.append(metadata_msg)
        
        # Single batch database write
        if messages_to_add:
            collection.update_one(
                {"conversation_id": conv_uuid},
                {
                    "$push": {"messages": {"$each": messages_to_add}},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            # Update cache
            if conv_uuid in app.state.cache_conversations:
                app.state.cache_conversations[conv_uuid].extend(cache_updates)
        
        logger.info(f"Processed chat for conversation: {conv_uuid}")
        return Response(content=pickle.dumps(out), media_type="application/octet-stream")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to process chat request")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        collection.find_one({}, {"_id": 1})
        return {"status": "healthy", "cache_size": len(app.state.cache_conversations)}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503, 
            content={"status": "unhealthy", "error": str(e)}
        )