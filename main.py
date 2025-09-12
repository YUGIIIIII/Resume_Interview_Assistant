import streamlit as st
from gemini_service import GeminiService
from pdf_processor import PDFProcessor
from prompts import PromptGenerator
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def main():
    st.set_page_config(
        page_title="Resume Interview Assistant",
        page_icon="🎯",
        layout="wide"
    )

    st.title("Resume Interview Assistant 🎯")

    # Initialize session state
    if 'company_name' not in st.session_state:
        st.session_state['company_name'] = ""
    if 'role_name' not in st.session_state:
        st.session_state['role_name'] = ""
    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []

    # Initialize services
    api_key = None
    try:
        # Try to get the API key from Streamlit secrets first
        api_key = st.secrets.get("GOOGLE_API_KEY")
    except FileNotFoundError:
        # If secrets.toml is not found, try environment variables
        api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        st.error("Google API key not found. Please set the GOOGLE_API_KEY in a secrets.toml file or as an environment variable.")
        st.stop()
    
    llm_service = GeminiService(api_key)
    pdf_processor = PDFProcessor()
    prompt_generator = PromptGenerator()

    # Sidebar
    with st.sidebar:
        st.header("About")
        st.write("""
        This tool helps you prepare for interviews by:
        - Analyzing your resume
        - Generating relevant interview questions
        - Providing preparation recommendations
        """)
        
        st.header("How to use")
        st.write("""
        1. Upload your resume (PDF format)
        2. Enter the company name and role
        3. Get interview preparation guide
        """)

    # Main layout
    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("Upload Resume")
        uploaded_file = st.file_uploader("Upload your resume (PDF)", type="pdf")
        if uploaded_file:
            st.success("Resume uploaded successfully!")

    with col2:
        st.header("Position Details")
        company_name = st.text_input("Company Name", value=st.session_state.get('company_name', ''))
        
        # Role selection
        role_name = st.text_input("Role/Position", 
            placeholder="e.g., Frontend Developer, Data Scientist, DevOps Engineer",
            value=st.session_state.get('role_name', '')
        )
        
        # Common role suggestions
        if not role_name:
            st.caption("Common roles:")
            role_cols = st.columns(3)
            roles = [
                "Frontend Developer",
                "Backend Developer",
                "Full Stack Developer",
                "Data Scientist",
                "DevOps Engineer",
                "Software Engineer"
            ]
            for i, role in enumerate(roles):
                if role_cols[i % 3].button(role, key=f"role_{i}", use_container_width=True):
                    st.session_state['role_name'] = role
                    role_name = role

    if uploaded_file and company_name and role_name:
        if st.button("Generate Interview Preparation", use_container_width=True):
            try:
                with st.spinner(f"Analyzing resume for {role_name} position at {company_name}..."):
                    # Process PDF and extract structured data
                    resume_text = pdf_processor.extract_text(uploaded_file)
                    structured_data = pdf_processor.get_structured_data(resume_text)
                    
                    # Store the inputs
                    st.session_state['company_name'] = company_name
                    st.session_state['role_name'] = role_name
                    
                    # Generate and process response
                    prompt = prompt_generator.generate_interview_prompt(
                        structured_data, 
                        company_name,
                        role_name
                    )
                    response = llm_service.generate_response(prompt, role_name)

                    # Format the initial response and add it to chat history
                    if response:
                        formatted_initial_response = {"role": "assistant", "parts": [{"text": response.text if hasattr(response, 'text') else str(response)}]}
                        st.session_state.chat_history.append(formatted_initial_response)
                    
                    # Display results
                    st.success(f"Analysis Complete for {role_name} position! 🎉")
                    
                    tabs = st.tabs(["📊 Skills", "🎯 Interview Guide", "📝 Details"])
                    
                    with tabs[0]:
                        st.subheader("Technical Skills")
                        skills_dict = structured_data.get('skills', {})
                        
                        if skills_dict.get('languages'):
                            st.write("🔤 Programming Languages:")
                            st.write(", ".join(skills_dict['languages']))
                        
                        if skills_dict.get('frameworks'):
                            st.write("🔧 Frameworks & Libraries:")
                            st.write(", ".join(skills_dict['frameworks']))
                        
                        if skills_dict.get('tools'):
                            st.write("🛠️ Tools & Technologies:")
                            st.write(", ".join(skills_dict['tools']))
                    
                    with tabs[1]:
                        st.subheader(f"AI Generated Interview Guide for {role_name}")
                        st.markdown(response)
                    
                    with tabs[2]:
                        st.subheader("Resume Sections")
                        sections = structured_data.get('sections', {})
                        if sections:
                            for section_name, content in sections.items():
                                with st.expander(f"📌 {section_name}", expanded=True):
                                    if content:
                                        for line in content:
                                            if 'GPA' in line or 'CGPA' in line:
                                                st.markdown(f"**{line}**")
                                            else:
                                                st.markdown(f"- {line}")
                                    else:
                                        st.info(f"No content found in {section_name}")
                        else:
                            st.warning("No sections found in the resume")
                    
                    # Download button
                    st.markdown("---")
                    if response:
                        st.download_button(
                            "📥 Download Complete Analysis",
                            response,
                            file_name=f"interview_prep_{company_name}_{role_name}.txt",
                            mime="text/plain"
                        )

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                st.error("Please try again or contact support if the problem persists.")
    
    # Chat Interface
    st.markdown("---")
    st.header("Ask Follow-up Questions")

    if not st.session_state['chat_history']:
        st.info("Generate an interview preparation guide first to start the chat.")

    # Display chat messages
    for message in st.session_state.chat_history:
        # Format the role for display
        display_role = "User" if message["role"] == "user" else "Assistant"
        with st.chat_message(display_role):
            # Extract content from the parts list for display
            content_text = ""
            for part in message.get("parts", []):
                st.markdown(part.get("text", ""))

    # Chat input
    if prompt := st.chat_input("Ask a question about the interview preparation or your resume..."):
        with st.chat_message("user"):
            st.session_state.chat_history.append({"role": "user", "parts": [{"text": prompt}]})
            st.markdown(prompt)

            # Pass the correctly formatted history to the chat function
        # Add a print statement here to inspect chat_history before the call
            print("Chat History before API call:", st.session_state.chat_history)
            response = llm_service.chat_with_history(st.session_state.chat_history, prompt) 
            st.markdown(response)

            # Format the assistant's response for the chat history
            formatted_assistant_response = {"role": "assistant", "parts": [{"text": response}]}
            st.session_state.chat_history.append(formatted_assistant_response)

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center'>
            <p>Made with ❤️ using Google Gemini and Streamlit</p>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()