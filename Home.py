import streamlit as st

# Page config
st.set_page_config(page_title="SuperPro Designer Web App", page_icon="🏭", layout="wide")

# Initialize session state for authentication
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Hide sidebar when not authenticated
if not st.session_state.authenticated:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {display: none}
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    # Welcome message and login form
    st.title("Welcome to SuperPro Web App")
    st.markdown("Please log in to access the tools.")
    
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        username = st.text_input("Username", key="username_input", label_visibility="visible")
        password = st.text_input("Password", type="password", key="password_input", label_visibility="visible")
        
        if username and password:
            if username == st.secrets["authentication"]["username"] and password == st.secrets["authentication"]["password"]:
                st.session_state.authenticated = True
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid username or password")
                st.stop()
        st.stop()

# Title and description
st.title("SuperPro Designer Web App")
st.markdown("""
Welcome to the SuperPro Designer Web App! This comprehensive toolkit is designed to enhance your SuperPro Designer experience with three specialized features:

### 🤖 User Manual Chatbot
- AI-powered assistant for instant SuperPro Designer guidance
- Get answers to specific questions about features and functionalities
- Access step-by-step instructions and best practices
- Learn from practical examples and use cases

### 📊 Techno-economic Report Generator
- Generate detailed technical and economic analysis reports
- Transform your SuperPro Designer data into comprehensive documentation
- Analyze capital investments, operating costs, and key performance indicators
- Get actionable insights and recommendations

### 📅 Scheduling Analyzer
- Optimize your process scheduling and resource utilization
- Identify bottlenecks and efficiency improvements
- Analyze equipment usage and maintenance strategies
- Get data-driven recommendations for batch campaign planning

Select a tool from the sidebar to get started with your analysis!
""")

# Add footer
st.markdown("---")
st.markdown("*Developed by Tommaso De Santis*")
