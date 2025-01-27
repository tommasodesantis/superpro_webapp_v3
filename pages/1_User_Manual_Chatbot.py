import streamlit as st
import os
from r2r import R2RClient
from utils.check_auth import check_auth

# Page config
st.set_page_config(page_title="User Manual Chatbot", page_icon="📚")

# Check authentication
check_auth()

# Title and description
st.title("SuperPro User Manual Chatbot")
with st.expander("Instructions", expanded=False):
    st.markdown("""
    Your intelligent assistant for SuperPro Designer guidance! This AI-powered chatbot helps you:

    - Find specific information from the SuperPro Designer manual instantly
    - Get step-by-step instructions for complex operations
    - Understand best practices and recommended workflows
    - Troubleshoot common issues and challenges

    Simply type your question below - for example:
    - "How do I set up a batch process simulation?"
    - "What's the difference between procedure and operation modes?"
    - "How can I optimize my equipment sizing?"
    - "What factors affect scheduling calculations?"

    The chatbot will provide clear, accurate answers with references to the official manual.
    """)

# Custom system prompt
custom_prompt = """You are a SuperPro Designer expert focused on helping users understand and utilize the software effectively. Your purpose is to:

1. Quickly retrieve and explain SuperPro Designer features and functionalities
2. Help users understand process modeling and simulation capabilities
3. Provide clear, practical guidance with proper references to the user manual

When responding:
- Always cite specific sections from the SuperPro Designer user manual
- Provide step-by-step instructions when applicable
- Highlight any limitations or specific requirements
- Include relevant examples or use cases when possible

Query: {query}

Context: {context}

Response:"""

def get_superpro_help(query, client):
    """Function to query the SuperPro Designer knowledge base"""
    try:
        response = client.retrieval.rag(
            query,
            rag_generation_config={
                "model": "openai/gpt-4o-mini",
                "temperature": 0.7,
                "stream": False
            },
            task_prompt_override=custom_prompt
        )
        
        if isinstance(response, dict) and 'results' in response:
            return response['results'].get('completion', '')
        else:
            return "Error: Unexpected response format"
    except Exception as e:
        return f"Error: {str(e)}"

# Main interface
# Initialize client
client = R2RClient("https://api.cloud.sciphi.ai")
os.environ["R2R_API_KEY"] = st.secrets["R2R_API_KEY"]

# Query input
user_query = st.text_input("Enter your SuperPro Designer question:", 
                          placeholder="e.g., How do I set up a batch process simulation?")

if user_query:
    with st.spinner("Generating response..."):
        response = get_superpro_help(user_query, client)
        st.markdown("### Response")
        st.markdown(response)
        
    # Add a divider
    st.markdown("---")
    
    # Show previous questions (if any)
    if 'previous_queries' not in st.session_state:
        st.session_state.previous_queries = []
    
    if user_query not in st.session_state.previous_queries:
        st.session_state.previous_queries.append(user_query)
    
    if st.session_state.previous_queries:
        st.markdown("### Previous Questions")
        for q in reversed(st.session_state.previous_queries[-5:]):  # Show last 5 questions
            st.text(f"• {q}")
