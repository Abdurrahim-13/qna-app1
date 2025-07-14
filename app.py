import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime
import hashlib
import yaml
from yaml.loader import SafeLoader
from fpdf import FPDF

# Configuration files
DATA_FILE = "qa_data.json"
USER_FILE = "users.yaml"

# Initialize session state
if "subjects" not in st.session_state:
    st.session_state.subjects = {}

if "current_user" not in st.session_state:
    st.session_state.current_user = None

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Load existing data
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

# Save data to file
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Initialize or load data
st.session_state.subjects = load_data()

# User management functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
            return yaml.safe_load(f) or {}
    return {}

def save_users(users):
    with open(USER_FILE, "w") as f:
        yaml.dump(users, f)

def register_user(username, password, email=None):
    users = load_users()
    if username in users:
        return False
    users[username] = {
        "password": hash_password(password),
        "email": email,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_users(users)
    return True

def verify_user(username, password):
    users = load_users()
    if username in users:
        return users[username]["password"] == hash_password(password)
    return False

# PDF Generation
def generate_pdf(data, username):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.cell(200, 10, txt=f"Q&A Export for {username}", ln=True, align='C')
    pdf.ln(10)
    
    for subject, qa_list in data.items():
        pdf.set_font("Arial", 'B', size=12)
        pdf.cell(200, 10, txt=subject, ln=True)
        pdf.set_font("Arial", size=11)
        
        for qa in qa_list:
            pdf.multi_cell(0, 10, txt=f"Q: {qa['question']}")
            pdf.multi_cell(0, 10, txt=f"A: {qa['answer']}")
            pdf.cell(0, 10, txt=f"Date: {qa['timestamp']}", ln=True)
            pdf.ln(5)
    
    pdf_file = f"qna_export_{username}.pdf"
    pdf.output(pdf_file)
    return pdf_file

# Authentication system
def authentication_section():
    st.title("🔒 Private Q&A Knowledge Base")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username", autocomplete="off")
            password = st.text_input("Password", type="password", autocomplete="off")
            if st.form_submit_button("Login"):
                if verify_user(username, password):
                    st.session_state.authenticated = True
                    st.session_state.current_user = username
                    st.rerun()
                else:
                    st.error("Invalid credentials")
    
    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("New Username", autocomplete="off")
            new_password = st.text_input("New Password", type="password", autocomplete="off")
            confirm_password = st.text_input("Confirm Password", type="password", autocomplete="off")
            email = st.text_input("Email (optional)", autocomplete="off")
            
            if st.form_submit_button("Register"):
                if new_password != confirm_password:
                    st.error("Passwords don't match!")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters")
                else:
                    if register_user(new_username, new_password, email):
                        st.success("Registration successful! Please login.")
                    else:
                        st.error("Username already exists")

# Filter data by current user
def get_user_data():
    all_data = st.session_state.subjects
    user_data = {}
    for subject, qa_list in all_data.items():
        user_qa = [qa for qa in qa_list if qa.get("created_by") == st.session_state.current_user]
        if user_qa:
            user_data[subject] = user_qa
    return user_data

# Main app function
def main_app():
    st.title("📚 Private Q&A Knowledge Base")
    st.write(f"Welcome, {st.session_state.current_user}!")
    
    # Sidebar for navigation
    st.sidebar.title("Menu")
    page = st.sidebar.radio("Go to", ["Add Q&A", "View My Q&As", "Search", "Export"])
    
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.current_user = None
        st.rerun()

    # Add Q&A Section
    def add_qa():
        st.subheader("Add New Question & Answer")
        
        subject = st.text_input("Subject/Topic", placeholder="e.g., Python, Math, History", key="subject_input")
        question = st.text_area("Your Question", placeholder="Enter your question here...", key="question_input")
        answer = st.text_area("Your Answer", placeholder="Enter the answer here...", height=200, key="answer_input")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save Q&A", type="primary"):
                if not subject or not question or not answer:
                    st.error("Please fill in all fields!")
                else:
                    if subject not in st.session_state.subjects:
                        st.session_state.subjects[subject] = []
                    
                    new_entry = {
                        "question": question,
                        "answer": answer,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "created_by": st.session_state.current_user
                    }
                    st.session_state.subjects[subject].append(new_entry)
                    save_data(st.session_state.subjects)
                    st.success("✅ Q&A saved successfully!")
                    st.balloons()
        with col2:
            if st.button("Clear Fields"):
                st.rerun()

    # View Q&As Section with editing
    def view_qa():
        st.subheader("My Q&As")
        
        user_data = get_user_data()
        
        if not user_data:
            st.warning("You haven't saved any Q&As yet. Add some first!")
            return
        
        selected_subject = st.selectbox(
            "Choose a subject",
            list(user_data.keys())
        )
        
        st.markdown(f"### 📌 {selected_subject}")
        qa_list = user_data[selected_subject]
        
        for i, qa in enumerate(qa_list, 1):
            with st.expander(f"Q{i}: {qa['question'][:50]}..."):
                st.markdown("#### ❓ Question:")
                st.write(qa["question"])
                
                st.markdown("#### 📝 Answer:")
                st.write(qa["answer"])
                
                st.caption(f"Saved on: {qa['timestamp']}")
                
                # Edit and Delete buttons
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"✏ Edit Q{i}", key=f"edit_{i}"):
                        st.session_state.editing = {
                            "subject": selected_subject,
                            "index": i-1,
                            "question": qa["question"],
                            "answer": qa["answer"]
                        }
                with col2:
                    if st.button(f"🗑 Delete Q{i}", key=f"delete_{i}"):
                        # Find the actual index in the full dataset
                        full_qa_list = st.session_state.subjects[selected_subject]
                        for idx, item in enumerate(full_qa_list):
                            if (item["question"] == qa["question"] and 
                                item["answer"] == qa["answer"] and
                                item.get("created_by") == st.session_state.current_user):
                                del st.session_state.subjects[selected_subject][idx]
                                save_data(st.session_state.subjects)
                                st.rerun()
                                break
        
        # Edit modal
        if "editing" in st.session_state:
            with st.form("edit_form"):
                st.subheader("Edit Q&A")
                new_question = st.text_area(
                    "Question",
                    value=st.session_state.editing["question"],
                    key="edit_question"
                )
                new_answer = st.text_area(
                    "Answer",
                    value=st.session_state.editing["answer"],
                    height=200,
                    key="edit_answer"
                )
                
                if st.form_submit_button("Save Changes"):
                    subject = st.session_state.editing["subject"]
                    # Find the actual index in the full dataset
                    full_qa_list = st.session_state.subjects[subject]
                    for idx, item in enumerate(full_qa_list):
                        if (item["question"] == st.session_state.editing["question"] and 
                            item["answer"] == st.session_state.editing["answer"] and
                            item.get("created_by") == st.session_state.current_user):
                            full_qa_list[idx]["question"] = new_question
                            full_qa_list[idx]["answer"] = new_answer
                            full_qa_list[idx]["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            save_data(st.session_state.subjects)
                            break
                    
                    del st.session_state.editing
                    st.rerun()
                
                if st.form_submit_button("Cancel"):
                    del st.session_state.editing
                    st.rerun()

    # Search functionality (user-specific)
    def search_qa():
        st.subheader("🔍 Search My Q&As")
        search_term = st.text_input("Enter search term")
        
        if search_term:
            user_data = get_user_data()
            results = []
            for subject, qa_list in user_data.items():
                for qa in qa_list:
                    if (search_term.lower() in qa["question"].lower() or 
                        search_term.lower() in qa["answer"].lower()):
                        results.append({
                            "Subject": subject,
                            "Question": qa["question"],
                            "Answer": qa["answer"],
                            "Date": qa["timestamp"]
                        })
            
            if results:
                st.write(f"Found {len(results)} results:")
                df = pd.DataFrame(results)
                st.dataframe(df, hide_index=True, use_container_width=True)
                
                # Export search results
                csv = df.to_csv(index=False)
                st.download_button(
                    "Download Search Results as CSV",
                    data=csv,
                    file_name="my_search_results.csv",
                    mime="text/csv"
                )
            else:
                st.info("No matching Q&As found in your collection.")

    # Export functionality (user-specific)
    def export_qa():
        st.subheader("📤 Export My Q&As")
        
        user_data = get_user_data()
        
        if not user_data:
            st.warning("No Q&As to export. Add some first!")
            return
        
        export_format = st.radio("Export format", ["CSV", "JSON", "PDF", "Markdown"])
        selected_subjects = st.multiselect(
            "Select subjects to export",
            list(user_data.keys())
        )
        
        if not selected_subjects:
            st.info("Please select at least one subject.")
            return
        
        if st.button("Generate Export"):
            export_data = {subj: user_data[subj] for subj in selected_subjects}
            
            if export_format == "CSV":
                data = []
                for subject, qa_list in export_data.items():
                    for qa in qa_list:
                        data.append({
                            "Subject": subject,
                            "Question": qa["question"],
                            "Answer": qa["answer"],
                            "Date": qa["timestamp"]
                        })
                df = pd.DataFrame(data)
                csv = df.to_csv(index=False)
                st.download_button(
                    "Download CSV",
                    data=csv,
                    file_name=f"my_qna_export_{st.session_state.current_user}.csv",
                    mime="text/csv"
                )
            
            elif export_format == "JSON":
                json_str = json.dumps(export_data, indent=4)
                st.download_button(
                    "Download JSON",
                    data=json_str,
                    file_name=f"my_qna_export_{st.session_state.current_user}.json",
                    mime="application/json"
                )
            
            elif export_format == "PDF":
                pdf_file = generate_pdf(export_data, st.session_state.current_user)
                with open(pdf_file, "rb") as f:
                    pdf_bytes = f.read()
                st.download_button(
                    "Download PDF",
                    data=pdf_bytes,
                    file_name=f"my_qna_export_{st.session_state.current_user}.pdf",
                    mime="application/pdf"
                )
                os.remove(pdf_file)  # Clean up
            
            elif export_format == "Markdown":
                md_content = f"# Q&A Export for {st.session_state.current_user}\n\n"
                for subject, qa_list in export_data.items():
                    md_content += f"## {subject}\n\n"
                    for qa in qa_list:
                        md_content += f"### {qa['question']}\n\n"
                        md_content += f"{qa['answer']}\n\n"
                        md_content += f"Date: {qa['timestamp']}\n\n---\n\n"
                st.download_button(
                    "Download Markdown",
                    data=md_content,
                    file_name=f"my_qna_export_{st.session_state.current_user}.md",
                    mime="text/markdown"
                )

    # Display selected page
    if page == "Add Q&A":
        add_qa()
    elif page == "View My Q&As":
        view_qa()
    elif page == "Search":
        search_qa()
    elif page == "Export":
        export_qa()

# Create required files if they don't exist
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

if not os.path.exists(USER_FILE):
    with open(USER_FILE, "w") as f:
        yaml.dump({}, f)

# Main execution
def main():
    if not st.session_state.authenticated:
        authentication_section()
    else:
        main_app()

if __name__ == "__main__":
    main()
