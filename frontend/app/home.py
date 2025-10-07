import streamlit as st
import requests
import uuid
import time
import pickle
from langchain_core.messages import HumanMessage, AIMessage
from io import BytesIO
from typing import Dict, List, Optional


def display_products(products_info_list):
    """Display product cards with optimized rendering"""
    if not products_info_list:
        return
        
    for product in products_info_list:
        with st.container():
            st.markdown("""
                <div style="background: linear-gradient(135deg, #0f1c3d 0%, #1a2d52 100%); 
                            padding: 1.5rem; 
                            border-radius: 15px; 
                            margin-bottom: 1.5rem;
                            border: 1px solid rgba(255,255,255,0.08);
                            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);">
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns([1, 3])

            with col1:
                try:
                    # Cache image loading
                    img_url = product['metadata']['thumbnailImage']
                    if img_url:
                        st.image(BytesIO((requests.get(img_url, timeout=5)).content), width=150)
                except Exception as e:
                    st.write("🖼️ Image unavailable")

            with col2:
                st.markdown(f"<h3 style='color: #fff; margin-top: 0;'>{product['metadata'].get('title', 'N/A')}</h3>", unsafe_allow_html=True)
                st.markdown(f"<p style='color: #ffd700;'><strong>🏷️ Brand:</strong> {product['metadata'].get('brand', 'N/A')}</p>", unsafe_allow_html=True)
                st.markdown(f"<p style='color: #e0e0e0;'>{product['metadata'].get('description', 'No description')}</p>", unsafe_allow_html=True)
                st.markdown(f"<p style='color: #ffd700;'>⭐ <strong>{product['metadata'].get('stars', 'N/A')}</strong> / 5.0</p>", unsafe_allow_html=True)
                
                url = product['metadata'].get('url', '#')
                st.markdown(f"<a href='{url}' style='color: #00d4ff; text-decoration: none; font-weight: bold;'>🛒 View on Amazon →</a>", unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)


def make_api_request(method: str, endpoint: str, payload: Dict, timeout: int = 10) -> Optional[Dict]:
    """Centralized API request handler with error handling"""
    try:
        url = f"http://product-recommender-backend-service:8000{endpoint}"
        
        if method.upper() == "GET":
            response = requests.get(url, json=payload, timeout=timeout)
        elif method.upper() == "POST":
            response = requests.post(url, json=payload, timeout=timeout)
        elif method.upper() == "DELETE":
            response = requests.delete(url, json=payload, timeout=timeout)
        else:
            st.error(f"❌ Unsupported HTTP method: {method}")
            return None
        
        if response.status_code == 200:
            return response.json() if method != "POST" or endpoint != "/chat" else response
        elif response.status_code == 422:
            data = response.json()
            if "details" in data and "user_identity" in data["details"]:
                st.error(f"❌ {data['details']['user_identity'][0]}")
            else:
                st.error(f"❌ Validation error: {data.get('detail', 'Unknown error')}")
        elif response.status_code == 404:
            st.error("❌ Resource not found")
        elif response.status_code == 500:
            st.error("❌ Server error occurred")
        else:
            st.error(f"❌ Request failed with status {response.status_code}")
        
        return None
        
    except requests.exceptions.Timeout:
        st.error("❌ Request timed out. Please try again.")
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to server. Is it running?")
    except Exception as e:
        st.error(f"❌ Request failed: {str(e)}")
    
    return None


def initialize_session_state():
    """Initialize all session state variables"""
    if "page" not in st.session_state:
        st.session_state.page = "home"
    if 'session_uuid' not in st.session_state:
        st.session_state.session_uuid = str(uuid.uuid4())
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'messages' not in st.session_state:
        st.session_state.messages = {}


def create_new_conversation(user_identity: Optional[str] = None) -> bool:
    """Create a new conversation and update session state"""
    new_uuid = str(uuid.uuid4())
    payload = {"uuid": new_uuid, "user_identity": user_identity or st.session_state.user}
    
    data = make_api_request("POST", "/conversations/new", payload)
    if data:
        st.session_state.session_uuid = new_uuid
        st.session_state.messages = data['conversation_history']
        return True
    return False


def delete_conversation(conv_id: str, user_identity: str) -> bool:
    """Delete a conversation from backend and update state"""
    response = make_api_request("DELETE", f"/conversations/{conv_id}", {})
    
    if response:
        # Remove from session state
        if conv_id in st.session_state.messages:
            del st.session_state.messages[conv_id]
        
        # If deleted conversation was the current one, switch to another or create new
        if st.session_state.session_uuid == conv_id:
            if st.session_state.messages:
                st.session_state.session_uuid = list(st.session_state.messages.keys())[0]
            else:
                # Create a new conversation if no conversations left
                create_new_conversation(user_identity)
        
        return True
    return False


def render_home_page():
    """Render the home/login page"""
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    st.markdown("""
        <h1 style='text-align: center; font-size: 4rem; margin-bottom: 0; 
                   color: #ffffff;
                   text-shadow: 0 0 20px rgba(102, 126, 234, 0.8), 0 0 40px rgba(118, 75, 162, 0.6);'>
            🛍️ Amazon Product Recommender
        </h1>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <h3 style='text-align: center; color: #e0e0e0; font-weight: 300; margin-top: 1rem;
                   text-shadow: 0 2px 10px rgba(0,0,0,0.5);'>
            Welcome! Please identify yourself to get started
        </h3>
    """, unsafe_allow_html=True)
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("<h4 style='color: #ffffff;'>👤 Enter your details</h4>", unsafe_allow_html=True)
        user_identifier = st.text_input(
            "Name or Email",
            placeholder="Enter your name or email address",
            key="user_input",
            help="This helps us save your conversation history",
            label_visibility="collapsed"
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("✨ Continue", type="primary", use_container_width=True):
            if user_identifier:
                payload = {"uuid": st.session_state.session_uuid, "user_identity": user_identifier}
                data = make_api_request("POST", "/conversations/new", payload)
                
                if data:
                    st.session_state.messages = data['conversation_history']
                    st.session_state.user = user_identifier
                    st.success("✅ Loading page!")
                    st.session_state.page = "chat"
                    time.sleep(0.5)
                    st.rerun()
            else:
                st.warning("⚠️ Please share your details or choose to continue as a guest")

        st.divider()
        
        if st.button("🎭 Continue as Guest (No history saved)", use_container_width=True):
            st.session_state.user = None
            st.session_state.page = "chat"
            time.sleep(0.5)
            st.rerun()
    
    with col2:
        st.info("""
        **💡 Why provide details?**
        
        ✅ Save your conversation history
        
        ✅ Continue where you left off
        
        ✅ Get personalized recommendations
        
        Or continue as guest without saving history.
        """)


def render_sidebar():
    """Render the sidebar with conversations"""
    with st.sidebar:
        st.markdown("""
            <h2 style='color: white; text-align: center; margin-bottom: 2rem;'>
                💬 Conversations
            </h2>
        """, unsafe_allow_html=True)
        
        if st.button("➕ New Chat", use_container_width=True):
            if create_new_conversation():
                st.rerun()
        
        st.divider()
        
        # Sort conversations by most recent first (if they have timestamps)
        sorted_conversations = sorted(
            st.session_state.messages.items(),
            key=lambda x: len(x[1]),  # Simple sort by message count
            reverse=True
        )
        
        for conv_id, msg_list in sorted_conversations:
            # Generate conversation name from first user message
            conv_name = "New Chat"
            if msg_list:
                for msg in msg_list:
                    if msg['role'] == 'user':
                        conv_name = msg['content'][:30] + ("..." if len(msg['content']) > 30 else "")
                        break
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                if st.button(f"📝 {conv_name}", key=f"conv_{conv_id}", use_container_width=True):
                    st.session_state.session_uuid = conv_id
                    st.rerun()
            
            with col2:
                if st.button("🗑️", key=f"delete_{conv_id}", type="secondary"):
                    if delete_conversation(conv_id, st.session_state.user):
                        st.rerun()


def render_chat_page():
    """Render the main chat interface"""
    st.markdown("""
        <h1 style='text-align: center; margin-bottom: 0;
                   color: #ffffff;
                   text-shadow: 0 0 20px rgba(102, 126, 234, 0.8), 0 0 40px rgba(118, 75, 162, 0.6);
                   font-size: 3rem;'>
            🛍️ Let's Get Chatting!
        </h1>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <p style='text-align: center; font-size: 1.2rem; color: #e0e0e0; margin-top: 0.5rem;
                  text-shadow: 0 2px 10px rgba(0,0,0,0.5);'>
            Describe what you want and find it
        </p>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)

    # Only render sidebar if user is logged in
    if st.session_state.user:
        render_sidebar()

    # Display existing messages
    current_messages = st.session_state.messages.get(st.session_state.session_uuid, [])
    
    for msg in current_messages:
        if msg['role'] == 'user':
            st.chat_message('user').markdown(msg['content'])
        elif msg['role'] == 'ai':
            st.chat_message('assistant').markdown(msg['content'])
        elif msg["role"] == "metadata":
            display_products(msg["content"])

    # Chat input
    user_chat_input = st.chat_input("💭 Enter your query here...", key="conversation_query")
    
    if user_chat_input:
        # Display user message immediately
        st.chat_message("user").markdown(user_chat_input)
        
        # Add to session state
        if st.session_state.session_uuid not in st.session_state.messages:
            st.session_state.messages[st.session_state.session_uuid] = []
        
        st.session_state.messages[st.session_state.session_uuid].append({
            "role": "user",
            "content": user_chat_input
        })
        
        # Make API request
        payload = {
            "uuid": st.session_state.session_uuid,
            "user_query": user_chat_input
        }

        response = make_api_request("POST", "/chat", payload)
        
        if response and response.status_code == 200:
            try:
                graph_output = pickle.loads(response.content)
                
                if graph_output and 'messages' in graph_output:
                    # Display AI response
                    for msg in graph_output['messages'][-1:]:
                        if isinstance(msg, AIMessage):
                            st.chat_message("assistant").markdown(msg.content)
                            st.session_state.messages[st.session_state.session_uuid].append({
                                "role": "ai",
                                "content": msg.content
                            })
                    
                    # Display products if available
                    if graph_output.get('matches_metadata'):
                        st.session_state.messages[st.session_state.session_uuid].append({
                            "role": "metadata",
                            "content": graph_output['matches_metadata']
                        })
                        display_products(graph_output['matches_metadata'])
                        
            except Exception as e:
                st.error(f"❌ Failed to process response: {str(e)}")


# Main app configuration
st.set_page_config(
    page_title="Amazon Product Recommender",
    page_icon="🛍️",
    layout="wide"
)

# Dark mode custom CSS
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #16213e 100%);
    }
    .stApp, .stMarkdown, p, span, label {
        color: #ffffff !important;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
        text-shadow: 2px 2px 8px rgba(0,0,0,0.5);
    }
    .stButton > button {
        background: linear-gradient(135deg, #4a5dc7 0%, #5a3d7a 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 0.75rem 2rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(74, 93, 199, 0.4) !important;
    }
    .stButton > button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 8px 25px rgba(74, 93, 199, 0.6) !important;
    }
    .stTextInput > div > div > input {
        background: rgba(20, 20, 30, 0.8) !important;
        border: 2px solid rgba(74, 93, 199, 0.4) !important;
        border-radius: 15px !important;
        padding: 0.75rem !important;
        color: white !important;
        transition: all 0.3s ease !important;
    }
    .stTextInput > div > div > input:focus {
        background: rgba(30, 30, 40, 0.9) !important;
        border-color: #4a5dc7 !important;
        box-shadow: 0 0 15px rgba(74, 93, 199, 0.4) !important;
    }
    .stTextInput > div > div > input::placeholder {
        color: rgba(255, 255, 255, 0.5) !important;
    }
    .stAlert {
        background: rgba(20, 20, 30, 0.6) !important;
        border-radius: 15px !important;
        border: 1px solid rgba(74, 93, 199, 0.3) !important;
        color: white !important;
    }
    .stChatMessage {
        background: rgba(20, 20, 30, 0.4) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 15px !important;
        padding: 1rem !important;
        margin: 0.5rem 0 !important;
        backdrop-filter: blur(10px) !important;
    }
    .stChatInput > div {
        background: rgba(255, 255, 255, 0.1) !important;
        border: 2px solid rgba(102, 126, 234, 0.5) !important;
        border-radius: 25px !important;
    }
    .stChatInput textarea {
        background: transparent !important;
        color: white !important;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d0d15 0%, #12121d 100%) !important;
        border-right: 1px solid rgba(74, 93, 199, 0.2) !important;
    }
    [data-testid="stSidebar"] button {
        background: rgba(74, 93, 199, 0.15) !important;
        color: white !important;
        border: 1px solid rgba(74, 93, 199, 0.3) !important;
        border-radius: 10px !important;
        margin: 0.5rem 0 !important;
        transition: all 0.3s ease !important;
    }
    [data-testid="stSidebar"] button:hover {
        background: rgba(74, 93, 199, 0.3) !important;
        transform: translateX(8px) !important;
        box-shadow: 0 4px 15px rgba(74, 93, 199, 0.4) !important;
    }
    [data-testid="stSidebar"] .stMarkdown {
        color: white !important;
    }
    hr {
        border: none !important;
        height: 2px !important;
        background: linear-gradient(90deg, transparent, #667eea, transparent) !important;
        margin: 2rem 0 !important;
    }
    [data-testid="column"] {
        background: rgba(20, 20, 30, 0.3) !important;
        border-radius: 15px !important;
        padding: 1.5rem !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
    }
    .stButton > button[kind="secondary"] {
        background: rgba(220, 53, 69, 0.2) !important;
        border: 1px solid rgba(220, 53, 69, 0.5) !important;
        color: #ff6b7a !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background: rgba(220, 53, 69, 0.4) !important;
        box-shadow: 0 4px 15px rgba(220, 53, 69, 0.5) !important;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
initialize_session_state()

# Route to appropriate page
if st.session_state.page == "home":
    render_home_page()
elif st.session_state.page == "chat":
    render_chat_page()