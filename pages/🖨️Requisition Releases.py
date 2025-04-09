import streamlit as st
import sqlite3
import pandas as pd
from fpdf import FPDF
import tempfile
import os
from datetime import datetime
import base64
from PIL import Image
import io

# Page configuration with custom theme and layout
st.set_page_config(
    page_title="📋 Requisition Manager",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        padding-bottom: 1rem;
        border-bottom: 2px solid #E5E7EB;
        margin-bottom: 2rem;
    }
    .subheader {
        font-size: 1.5rem;
        color: #1E3A8A;
        padding-top: 1rem;
        padding-bottom: 0.5rem;
    }
    .card {
        background-color: #F3F4F6;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    .info-text {
        color: #4B5563;
    }
    .stButton>button {
        background-color: #1E3A8A;
        color: white;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #2563EB;
        border-color: #2563EB;
    }
    .success {
        background-color: #D1FAE5;
        padding: 15px;
        border-radius: 5px;
        color: #065F46;
        font-weight: bold;
        margin: 10px 0;
    }
    div[data-testid="stDataFrame"] div[data-testid="stHorizontalBlock"] {
        background-color: #F9FAFB;
    }
    div[data-testid="stDataFrame"] th {
        background-color: #1E3A8A;
        color: white;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Create a header with logo placeholder
st.markdown('<div class="main-header">📋 Requisition Manager</div>', unsafe_allow_html=True)
st.markdown('<p class="info-text">Browse, update, and export requisition forms with enhanced visual styling</p>',
            unsafe_allow_html=True)


# --- DB access functions ---
def load_requisitions():
    conn = sqlite3.connect("db.db")
    df = pd.read_sql_query("SELECT * FROM requisitions ORDER BY timestamp DESC", conn)
    conn.close()
    return df


def update_requisition(record_id, title, description, quantity, unit, request_date):
    conn = sqlite3.connect("db.db")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE requisitions
        SET title = ?, description = ?, quantity = ?, unit = ?, request_date = ?
        WHERE id = ?
    """, (title, description, quantity, unit, request_date, record_id))
    conn.commit()
    conn.close()


# --- Better structured PDF Generator to avoid text overlap ---
def generate_pdf(row):
    class BeautifulPDF(FPDF):
        def __init__(self):
            super().__init__()
            # Set document properties
            self.set_auto_page_break(auto=True, margin=15)
            self.set_margins(left=10, top=10, right=10)

            # Define colors for consistent use
            self.blue_dark = (30, 58, 138)
            self.blue_medium = (59, 130, 246)
            self.gray_light = (240, 240, 240)
            self.gray_text = (75, 85, 99)
            self.black = (0, 0, 0)

        def header(self):
            # Create a professional header with styling
            self.set_font('Arial', 'B', 16)
            self.set_text_color(*self.blue_dark)

            # Add a blue rectangle header background
            self.set_fill_color(*self.blue_dark)
            self.rect(10, 10, 190, 20, 'F')

            # Add title text in white
            self.set_text_color(255, 255, 255)
            self.set_xy(15, 15)
            self.cell(180, 10, 'MATERIAL REQUISITION', 0, 0, 'C')

            # Add a secondary title below
            self.set_font('Arial', 'I', 10)
            self.set_text_color(*self.gray_text)
            self.set_xy(10, 32)
            self.cell(190, 6, 'Requisition Management System', 0, 0, 'C')

            # Add a line separator
            self.set_draw_color(*self.blue_medium)
            self.set_line_width(0.5)
            self.line(10, 40, 200, 40)

            # Set the position for the content to begin
            self.set_y(45)

        def footer(self):
            # Position at 1.5 cm from bottom
            self.set_y(-15)
            # Arial italic 8
            self.set_font('Arial', 'I', 8)
            self.set_text_color(*self.gray_text)
            # Page number
            self.cell(95, 10, f'Generated on {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 0, 'L')
            self.cell(95, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'R')

        def add_section_title(self, title):
            # Style section titles with blue background
            self.set_font('Arial', 'B', 12)
            self.set_fill_color(*self.blue_medium)
            self.set_text_color(255, 255, 255)
            self.cell(0, 10, title, 0, 1, 'L', 1)
            self.ln(2)  # Add a small space after the title

        def add_info_field(self, title, value, width=90):
            # Create a labeled field for information
            self.set_font('Arial', 'B', 10)
            self.set_text_color(*self.blue_dark)
            self.cell(40, 8, f"{title}:", 0, 0)

            # Set text style for the value
            self.set_font('Arial', '', 10)
            self.set_text_color(*self.black)

            # For multi-line text (like descriptions)
            if len(str(value)) > 50 or title == "Description":
                self.ln()
                self.set_x(20)  # Indent the description
                self.set_fill_color(*self.gray_light)
                self.multi_cell(width, 6, str(value), 0, 'L', 1)
                self.ln(2)  # Add space after the description
            else:
                self.cell(width - 40, 8, str(value), 0, 1)

    # Initialize PDF
    pdf = BeautifulPDF()
    pdf.alias_nb_pages()
    pdf.add_page()

    # Add requisition ID (reference number)
    pdf.set_font('Arial', 'B', 10)
    pdf.set_text_color(*pdf.blue_dark)
    ref_id = f"REQ-{row.get('id', 1000):04d}"
    pdf.cell(0, 8, f"Reference: {ref_id}", 0, 1, 'R')
    pdf.ln(5)

    # Requisition Details Section
    pdf.add_section_title("REQUISITION DETAILS")

    # Left column fields
    pdf.add_info_field("Title", row["title"])
    pdf.add_info_field("Description", row["description"])
    pdf.add_info_field("Quantity", f"{row['quantity']} {row['unit']}")

    # Add some space before date information
    pdf.ln(5)

    # Date information
    pdf.add_info_field("Request Date", row["request_date"])
    pdf.add_info_field("Timestamp", row["timestamp"])

    # Add some space before signature section
    pdf.ln(15)

    # Signature section with proper spacing
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(*pdf.blue_dark)
    pdf.cell(0, 10, "SIGNATURES", 0, 1, 'L')

    # Draw signature lines
    pdf.set_draw_color(*pdf.blue_medium)

    # Calculate positions for signature lines
    sig_y = pdf.get_y() + 15

    # First signature (Requested By)
    pdf.line(20, sig_y, 85, sig_y)
    pdf.set_xy(20, sig_y + 2)
    pdf.set_font('Arial', '', 9)
    pdf.cell(65, 5, "Requested By", 0, 0, 'C')

    # Second signature (Approved By)
    pdf.line(115, sig_y, 180, sig_y)
    pdf.set_xy(115, sig_y + 2)
    pdf.set_font('Arial', '', 9)
    pdf.cell(65, 5, "Approved By", 0, 1, 'C')

    # Add date lines for signatures
    sig_date_y = sig_y + 15
    pdf.set_font('Arial', '', 8)

    # First date line
    pdf.line(20, sig_date_y, 85, sig_date_y)
    pdf.set_xy(20, sig_date_y + 2)
    pdf.cell(65, 5, "Date", 0, 0, 'C')

    # Second date line
    pdf.line(115, sig_date_y, 180, sig_date_y)
    pdf.set_xy(115, sig_date_y + 2)
    pdf.cell(65, 5, "Date", 0, 1, 'C')

    # Add terms and conditions
    pdf.ln(25)
    pdf.add_section_title("TERMS AND CONDITIONS")

    pdf.set_font('Arial', '', 9)
    terms_text = """1. All requisitions must be approved before procurement.
2. Items will be procured based on company policies and procedures.
3. Delivery timelines depend on item availability and supplier terms.
4. For any questions regarding this requisition, please contact the procurement department."""

    pdf.set_fill_color(*pdf.blue_medium)
    pdf.multi_cell(0, 6, terms_text, 0, 'L', 1)

    # Output the PDF to a file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
        pdf.output(tmpfile.name)
        return tmpfile.name


# --- Load Data ---
df = load_requisitions()

# Show requisitions in two columns layout
col1, col2 = st.columns([2, 3])

with col1:
    st.markdown('<div class="subheader">📝 Requisition List</div>', unsafe_allow_html=True)

    if df.empty:
        st.info("No requisitions found in the database.")
    else:
        # Format the dataframe for better display
        display_df = df.copy()
        display_df["timestamp"] = pd.to_datetime(display_df["timestamp"]).dt.strftime("%Y-%m-%d %H:%M")
        display_df["request_date"] = pd.to_datetime(display_df["request_date"]).dt.strftime("%Y-%m-%d")

        # Show a simplified view for selection
        st.dataframe(
            display_df[["id", "title", "quantity", "unit", "request_date"]],
            use_container_width=True,
            height=400
        )

        selected_id = st.selectbox(
            "Select a requisition to view/edit",
            df["id"],
            format_func=lambda x: f"REQ-{x:04d}: {df[df['id'] == x].iloc[0]['title']}"
        )

with col2:
    if not df.empty:
        selected_row = df[df["id"] == selected_id].iloc[0]

        # Try parsing the date safely
        try:
            parsed_date = datetime.strptime(selected_row["request_date"], "%Y-%m-%d").date()
        except Exception:
            parsed_date = datetime.today().date()

        st.markdown(f'<div class="subheader">📋 Edit Requisition #{selected_id}</div>', unsafe_allow_html=True)

        # We'll use a flag to handle download outside the form
        download_triggered = False

        st.markdown('<div class="card">', unsafe_allow_html=True)
        with st.form("edit_form"):
            new_title = st.text_input("Title", value=selected_row["title"])
            new_description = st.text_area("Description", value=selected_row["description"], height=150)

            col1, col2 = st.columns(2)
            with col1:
                new_quantity = st.number_input("Quantity", min_value=1, value=selected_row["quantity"])
            with col2:
                new_unit = st.text_input("Unit", value=selected_row["unit"])

            new_request_date = st.date_input("Requested Date", value=parsed_date)

            col1, col2 = st.columns(2)
            with col1:
                save_clicked = st.form_submit_button("💾 Save Changes")
            with col2:
                download_triggered = st.form_submit_button("🖨️ Generate PDF")

            if save_clicked:
                update_requisition(selected_id, new_title, new_description, new_quantity, new_unit,
                                   str(new_request_date))
                st.markdown('<div class="success">✅ Requisition updated successfully!</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Now safely trigger download AFTER form, since it's not allowed inside
        if download_triggered:
            updated_row = {
                "id": selected_id,  # Pass the ID for reference number
                "title": new_title,
                "description": new_description,
                "quantity": new_quantity,
                "unit": new_unit,
                "request_date": str(new_request_date),
                "generated_by_ai": selected_row.get("generated_by_ai", False),
                "timestamp": selected_row["timestamp"]
            }

            # Generate and provide PDF
            with st.spinner("Generating PDF..."):
                pdf_path = generate_pdf(updated_row)
                with open(pdf_path, "rb") as f:
                    pdf_data = f.read()
                    st.download_button(
                        label="📄 Download PDF",
                        data=pdf_data,
                        file_name=f"requisition_{selected_id}.pdf",
                        mime="application/pdf",
                        key="pdf_download"
                    )

                    # Preview the PDF
                    st.markdown("### 👁️ PDF Preview")
                    b64_pdf = base64.b64encode(pdf_data).decode("utf-8")
                    pdf_display = f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="500" type="application/pdf"></iframe>'
                    st.markdown(pdf_display, unsafe_allow_html=True)

                os.remove(pdf_path)
    else:
        st.info("Select a requisition from the list to view and edit.")

# Add a stats section at the bottom
if not df.empty:
    st.markdown('<div class="subheader">📊 Requisition Statistics</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Requisitions", len(df))

    with col2:
        ai_generated = df["generated_by_ai"].sum() if "generated_by_ai" in df.columns else 0
        ai_percent = int(ai_generated / len(df) * 100) if len(df) > 0 else 0
        st.metric("AI Generated", f"{ai_generated} ({ai_percent}%)")

    with col3:
        today = datetime.today().date()
        recent = df[pd.to_datetime(df["timestamp"]).dt.date >= today - pd.Timedelta(days=7)]
        st.metric("Last 7 Days", len(recent))