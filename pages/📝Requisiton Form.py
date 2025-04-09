import streamlit as st
import sqlite3
from datetime import datetime, date
from openai import OpenAI

# --- OpenAI setup ---
client = OpenAI()

# --- DB setup ---
def init_db():
    conn = sqlite3.connect('../db.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS requisitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            quantity INTEGER,
            unit TEXT,
            request_date TEXT,
            generated_by_ai BOOLEAN,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def insert_requisition(title, description, quantity, unit, request_date, generated_by_ai):
    conn = sqlite3.connect('db.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO requisitions (title, description, quantity, unit, request_date, generated_by_ai)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (title, description, quantity, unit, request_date, generated_by_ai))
    conn.commit()
    conn.close()

init_db()

# --- Streamlit UI ---
st.set_page_config(page_title="Procurement Requisition Portal", layout="wide")
st.title("📦 Procurement Requisition Portal")
st.markdown("Use LLM to generate or manually fill the requisition form for materials procurement.")

tab1, tab2 = st.tabs(["✨ Auto-generate with AI", "✍️ Manual Entry"])

# --- Tab 1: AI-generated form ---
with tab1:
    st.subheader("LLM-assisted Requisition Generation")
    user_input = st.text_area("Describe your requisition needs:",
                              placeholder="e.g. 100 boxes of Nitrile Gloves for warehouse staff use, available in 10 days.")

    if st.button("🔮 Generate Requisition"):
        if not user_input.strip():
            st.warning("Please enter a description first.")
        else:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a structured requisition generator. Return only structured data in this exact format, without inferring dates. Always use today's date."
                    },
                    {
                        "role": "user",
                        "content": f"""
                Please generate a structured requisition in this exact format, using today's date (not inferred) and substituting placeholders with information from the request. Do not infer dates based on availability or urgency. Always default dates to the current day.

                Requisition No: [leave blank]  
                Requisition Date: {date.today().strftime("%Y-%m-%d")}  
                Requester Name: [inferred]  
                Department: [inferred]  
                Material ID: [optional]  
                Title: [short item name]  
                Description: [longer explanation]  
                Size: [dimensions]  
                Quantity: [integer]  
                Unit: [pcs, box, etc]  
                Required By Date: {date.today().strftime("%Y-%m-%d")}  
                Justification for Requirement: [reason]  
                Approved By: [optional]  

                Request: {user_input}
                """
                    }
                ],
                temperature=0
            )
            st.session_state.generated_text = response.choices[0].message.content

    if "generated_text" in st.session_state:
        gen_text = st.session_state.generated_text
        st.success("Generated Requisition:")
        st.code(gen_text)

        with st.form("ai_generated_form"):
            st.markdown("### Confirm and Submit the AI-Generated Requisition")

            # Parse fields
            def extract(field_name, default=""):
                for line in gen_text.splitlines():
                    if field_name in line:
                        return line.split(":", 1)[-1].strip()
                return default

            title = st.text_input("Title", value=extract("Title"))
            description = st.text_area("Description", value=gen_text)
            quantity = st.number_input("Quantity", min_value=1, step=1, value=int(extract("Quantity", "1")))
            unit = st.text_input("Unit", value=extract("Unit", "pcs"))
            size = st.text_input("Size", value=extract("Size"))
            requester = st.text_input("Requester Name", value=extract("Requester Name"))
            department = st.text_input("Department", value=extract("Department"))
            justification = st.text_area("Justification for Requirement", value=extract("Justification for Requirement"))

            from datetime import date  # Make sure this is at the top

            from datetime import date

            request_date = st.date_input("Required By Date", value=date.today())
            confirm = st.form_submit_button("📥 Confirm & Save")
            st.session_state["request_date"] = request_date

            if confirm:
                insert_requisition(
                    title=title,
                    description=description,
                    quantity=quantity,
                    unit=unit,
                    request_date=st.session_state["request_date"],
                    generated_by_ai=True
                )
                st.success("Requisition submitted and saved ✅")
                del st.session_state["generated_text"]
                del st.session_state["request_date"]

# --- Tab 2: Manual form ---
with tab2:
    st.subheader("Manual Requisition Form")
    with st.form("manual_form"):
        title = st.text_input("Title")
        description = st.text_area("Description")
        quantity = st.number_input("Quantity", min_value=1, step=1)
        unit = st.text_input("Unit", value="pcs")
        request_date = st.date_input("Required By Date", value=date.today())
        submitted = st.form_submit_button("📥 Submit Requisition")

        if submitted:
            insert_requisition(title, description, quantity, unit, request_date.strftime("%Y-%m-%d"), False)
            st.success("Requisition submitted and saved ✅")