import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import openai
import json
import os


# Helper functions for displaying approval tabs
def display_all(matches):
    st.markdown("### All Vendor Assignments")

    # Format for display
    display_df = matches.copy()
    display_df['match_score'] = (display_df['match_score'] * 100).round().astype(int).astype(str) + "%"
    display_df['created_at'] = pd.to_datetime(display_df['created_at']).dt.strftime("%Y-%m-%d %H:%M")
    display_df['approved_at'] = pd.to_datetime(display_df['approved_at']).apply(
        lambda x: x.strftime("%Y-%m-%d %H:%M") if not pd.isna(x) else ""
    )

    # Show the dataframe
    st.dataframe(
        display_df[[
            'id', 'requisition_id', 'requisition_title',
            'vendor_id', 'vendor_name', 'match_score',
            'status', 'created_at', 'approved_at'
        ]],
        use_container_width=True,
        height=400
    )

    # Allow choosing a match to see details
    selected_match_id = st.selectbox(
        "Select a vendor assignment to view details",
        matches['id'],
        format_func=lambda
            x: f"Match #{x}: {matches[matches['id'] == x].iloc[0]['vendor_name']} for {matches[matches['id'] == x].iloc[0]['requisition_title']}"
    )

    if selected_match_id:
        display_match_details(matches[matches['id'] == selected_match_id].iloc[0])


def display_pending(matches):
    st.markdown("### Pending Vendor Assignments")

    for _, match in matches.iterrows():
        match_id = match['id']
        match_score = int(match['match_score'] * 100)

        st.markdown(f"""
        <div class='vendor-match'>
            <div class='vendor-match-title'>
                REQ-{match['requisition_id']:04d}: {match['requisition_title']} → {match['vendor_name']}
                <span class='match-score'>{match_score}% Match</span>
            </div>
            <div><strong>Match Reason:</strong> {match['match_reason']}</div>
            <div style='margin-top:5px;'><strong>Created:</strong> {pd.to_datetime(match['created_at']).strftime('%Y-%m-%d %H:%M')}</div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"✅ Approve", key=f"approve_{match_id}"):
                update_vendor_match_status(match_id, "approved")
                st.success(f"Vendor match #{match_id} approved successfully!")
                st.rerun()
        with col2:
            if st.button(f"❌ Reject", key=f"reject_{match_id}"):
                update_vendor_match_status(match_id, "rejected")
                st.success(f"Vendor match #{match_id} rejected.")
                st.rerun()

        st.markdown("---")


def display_approved(matches):
    st.markdown("### Approved Vendor Assignments")

    for _, match in matches.iterrows():
        match_id = match['id']
        match_score = int(match['match_score'] * 100)

        st.markdown(f"""
        <div class='vendor-match'>
            <div class='vendor-match-title'>
                REQ-{match['requisition_id']:04d}: {match['requisition_title']} → {match['vendor_name']}
                <span class='match-score'>{match_score}% Match</span>
                <span class='approval-approved' style='padding:3px 8px;border-radius:4px;margin-left:10px;'>APPROVED</span>
            </div>
            <div><strong>Match Reason:</strong> {match['match_reason']}</div>
            <div style='margin-top:5px;'>
                <strong>Created:</strong> {pd.to_datetime(match['created_at']).strftime('%Y-%m-%d %H:%M')} | 
                <strong>Approved:</strong> {pd.to_datetime(match['approved_at']).strftime('%Y-%m-%d %H:%M')}
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button(f"❌ Revoke Approval", key=f"revoke_{match_id}"):
            update_vendor_match_status(match_id, "pending")
            st.success(f"Approval revoked. Vendor match #{match_id} is now pending.")
            st.rerun()

        st.markdown("---")


def display_rejected(matches):
    st.markdown("### Rejected Vendor Assignments")

    for _, match in matches.iterrows():
        match_id = match['id']
        match_score = int(match['match_score'] * 100)

        st.markdown(f"""
        <div class='vendor-match'>
            <div class='vendor-match-title'>
                REQ-{match['requisition_id']:04d}: {match['requisition_title']} → {match['vendor_name']}
                <span class='match-score'>{match_score}% Match</span>
                <span class='approval-rejected' style='padding:3px 8px;border-radius:4px;margin-left:10px;'>REJECTED</span>
            </div>
            <div><strong>Match Reason:</strong> {match['match_reason']}</div>
            <div style='margin-top:5px;'>
                <strong>Created:</strong> {pd.to_datetime(match['created_at']).strftime('%Y-%m-%d %H:%M')} | 
                <strong>Rejected:</strong> {pd.to_datetime(match['approved_at']).strftime('%Y-%m-%d %H:%M')}
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button(f"🔄 Reconsider", key=f"reconsider_{match_id}"):
            update_vendor_match_status(match_id, "pending")
            st.success(f"Vendor match #{match_id} returned to pending status.")
            st.rerun()

        st.markdown("---")


def display_match_details(match):
    st.markdown(f"### Match Details #{match['id']}")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Requisition Details")
        st.markdown(f"**ID:** REQ-{match['requisition_id']:04d}")
        st.markdown(f"**Title:** {match['requisition_title']}")

    with col2:
        st.markdown("#### Vendor Details")
        st.markdown(f"**ID:** {match['vendor_id']}")
        st.markdown(f"**Name:** {match['vendor_name']}")
        st.markdown(f"**Email:** {match['vendor_email']}")

    st.markdown("#### Match Information")
    st.markdown(f"**Match Score:** {int(match['match_score'] * 100)}%")
    st.markdown(f"**Match Reason:** {match['match_reason']}")
    st.markdown(f"**Status:** {match['status'].upper()}")
    st.markdown(f"**Created:** {pd.to_datetime(match['created_at']).strftime('%Y-%m-%d %H:%M')}")

    if match['approved_at']:
        st.markdown(f"**Decision Date:** {pd.to_datetime(match['approved_at']).strftime('%Y-%m-%d %H:%M')}")

    st.markdown("#### Actions")
    col1, col2, col3 = st.columns(3)

    with col1:
        if match['status'] != "approved":
            if st.button("✅ Approve", key=f"detail_approve_{match['id']}"):
                update_vendor_match_status(match['id'], "approved")
                st.success(f"Vendor match #{match['id']} approved successfully!")
                st.rerun()

    with col2:
        if match['status'] != "pending":
            if st.button("🔄 Set Pending", key=f"detail_pending_{match['id']}"):
                update_vendor_match_status(match['id'], "pending")
                st.success(f"Vendor match #{match['id']} set to pending.")
                st.rerun()

    with col3:
        if match['status'] != "rejected":
            if st.button("❌ Reject", key=f"detail_reject_{match['id']}"):
                update_vendor_match_status(match['id'], "rejected")
                st.success(f"Vendor match #{match['id']} rejected.")
                st.rerun()

# Page configuration
st.set_page_config(
    page_title="🤝 Vendor Assignment",
    page_icon="🤝",
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
    .warning {
        background-color: #FEF3C7;
        padding: 15px;
        border-radius: 5px;
        color: #92400E;
        font-weight: bold;
        margin: 10px 0;
    }
    .error {
        background-color: #FEE2E2;
        padding: 15px;
        border-radius: 5px;
        color: #B91C1C;
        font-weight: bold;
        margin: 10px 0;
    }
    .vendor-match {
        background-color: #EFF6FF;
        border-left: 4px solid #3B82F6;
        padding: 15px;
        margin: 10px 0;
        border-radius: 0 5px 5px 0;
    }
    .vendor-match-title {
        font-weight: bold;
        color: #1E3A8A;
        margin-bottom: 5px;
    }
    .match-score {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.8rem;
        font-weight: bold;
        margin-left: 10px;
        color: white;
        background-color: #3B82F6;
    }
    .approval-pending {
        color: #92400E;
        background-color: #FEF3C7;
    }
    .approval-approved {
        color: #065F46;
        background-color: #D1FAE5;
    }
    .approval-rejected {
        color: #B91C1C;
        background-color: #FEE2E2;
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

# Page header
st.markdown('<div class="main-header">🤝 Vendor Assignment</div>', unsafe_allow_html=True)
st.markdown('<p class="info-text">Automatically assign vendors to requisitions and manage approval process</p>',
            unsafe_allow_html=True)


# Initialize database connection
@st.cache_resource
def init_db_connection():
    conn = sqlite3.connect('db.db', check_same_thread=False)

    # Create requisition_vendors table if it doesn't exist
    conn.execute("""
        CREATE TABLE IF NOT EXISTS requisition_vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            requisition_id INTEGER,
            vendor_id INTEGER,
            match_score REAL,
            match_reason TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            approved_at TEXT,
            FOREIGN KEY (requisition_id) REFERENCES requisitions (id),
            FOREIGN KEY (vendor_id) REFERENCES vendors (id)
        )
    """)

    return conn


conn = init_db_connection()


# Load data
def load_requisitions():
    df = pd.read_sql_query("""
        SELECT r.*, 
               COUNT(rv.id) as vendor_count,
               SUM(CASE WHEN rv.status = 'approved' THEN 1 ELSE 0 END) as approved_count
        FROM requisitions r
        LEFT JOIN requisition_vendors rv ON r.id = rv.requisition_id
        GROUP BY r.id
        ORDER BY r.timestamp DESC
    """, conn)
    return df


def load_vendors():
    df = pd.read_sql_query("SELECT * FROM vendors ORDER BY name", conn)
    return df


def load_requisition_vendors(requisition_id):
    df = pd.read_sql_query("""
        SELECT rv.*, v.name as vendor_name, v.email as vendor_email, v.description as vendor_description
        FROM requisition_vendors rv
        JOIN vendors v ON rv.vendor_id = v.id
        WHERE rv.requisition_id = ?
        ORDER BY rv.match_score DESC
    """, conn, params=(requisition_id,))
    return df


# OpenAI integration
def get_openai_key():
    # In a real app, you would use a more secure way to store this
    # This is just for demonstration
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        key = st.session_state.get("openai_api_key", "")
    return key


def set_openai_key(key):
    st.session_state["openai_api_key"] = key
    os.environ["OPENAI_API_KEY"] = key


def match_vendors_to_requisition(requisition, vendors, api_key):
    # Configure OpenAI with the API key
    client = openai.OpenAI(api_key=api_key)

    # Prepare vendor data for the prompt
    vendor_data = "\n\n".join([
        f"Vendor {v['id']}: {v['name']}\nDescription: {v['description']}"
        for _, v in vendors.iterrows()
    ])

    # Construct prompt
    prompt = f"""
You are an AI procurement assistant that matches requisitions to the most suitable vendors based on the requisition description and vendor capabilities.

REQUISITION DETAILS:
Title: {requisition['title']}
Description: {requisition['description']}
Quantity: {requisition['quantity']} {requisition['unit']}

AVAILABLE VENDORS:
{vendor_data}

INSTRUCTIONS:
1. Analyze the requisition details and identify key requirements.
2. Evaluate each vendor's suitability based on their description.
3. Select the top 3 most suitable vendors for this requisition.
4. For each selected vendor, provide:
   - Vendor ID
   - Match score (0.0 to 1.0, where 1.0 is perfect match)
   - A brief explanation of why this vendor is suitable

OUTPUT FORMAT:
Provide your response in JSON format as follows:
[
  {{
    "vendor_id": <id>,
    "match_score": <score>,
    "match_reason": "<explanation>"
  }},
  ...
]
Do not include any other text in your response besides this JSON.
"""

    try:
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system",
                 "content": "You are a procurement specialist AI that matches requisitions to suitable vendors. There can be more than one match. Return a list of dicts, even if you only have one return value."},
                {"role": "user", "content": prompt}
            ],

        )

        # Extract and parse the response
        result_text = response.choices[0].message.content
        #st.write(result_text)

        # Clean the response if it contains markdown code blocks
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()

        # Parse the JSON
        results = json.loads(result_text)
        #st.write(results)

        # Ensure we have a list of matches
        if isinstance(results, dict) and "matches" in results:
            return results["matches"]
        elif isinstance(results, list):
            return results
        else:
            return []

    except Exception as e:
        st.error(f"Error calling OpenAI API: {str(e)}")
        return []


# Database operations
def save_vendor_matches(requisition_id, matches):
    cursor = conn.cursor()

    # Delete existing matches that are still pending
    cursor.execute(
        "DELETE FROM requisition_vendors WHERE requisition_id = ? AND status = 'pending'",
        (requisition_id,)
    )

    # Insert new matches
    for match in matches:
        cursor.execute(
            """
            INSERT INTO requisition_vendors 
            (requisition_id, vendor_id, match_score, match_reason, status, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?)
            """,
            (
                requisition_id,
                match["vendor_id"],
                match["match_score"],
                match["match_reason"],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )

    conn.commit()
    return True


def update_vendor_match_status(match_id, status):
    cursor = conn.cursor()

    # Update the status and approval timestamp
    cursor.execute(
        """
        UPDATE requisition_vendors 
        SET status = ?, approved_at = ?
        WHERE id = ?
        """,
        (status, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), match_id)
    )

    conn.commit()
    return True


# Main layout
tab1, tab2 = st.tabs(["📋 Assign Vendors", "✅ Approval Management"])

with tab1:
    # OpenAI API Key input


    # Load data
    requisitions = load_requisitions()
    vendors = load_vendors()

    if vendors.empty:
        st.warning("No vendors found in the database. Please add vendors first.")
    elif requisitions.empty:
        st.info("No requisitions found. Create requisitions before assigning vendors.")
    else:
        # Two column layout
        col1, col2 = st.columns([2, 3])

        with col1:
            st.markdown('<div class="subheader">📝 Requisition List</div>', unsafe_allow_html=True)

            # Format the dataframe for better display
            display_df = requisitions.copy()
            display_df["timestamp"] = pd.to_datetime(display_df["timestamp"]).dt.strftime("%Y-%m-%d %H:%M")
            display_df["request_date"] = pd.to_datetime(display_df["request_date"]).dt.strftime("%Y-%m-%d")

            # Add vendor status column
            display_df["vendor_status"] = display_df.apply(
                lambda row: f"{row['approved_count']}/{row['vendor_count']}" if row['vendor_count'] > 0 else "None",
                axis=1
            )

            # Show a simplified view for selection
            st.dataframe(
                display_df[["id", "title", "quantity", "unit", "vendor_status"]],
                use_container_width=True,
                height=400
            )

            selected_id = st.selectbox(
                "Select a requisition to assign vendors",
                requisitions["id"],
                format_func=lambda x: f"REQ-{x:04d}: {requisitions[requisitions['id'] == x].iloc[0]['title']}"
            )

            # Process vendor assignment button
            if get_openai_key():
                if st.button("🤖 Auto-Assign Vendors"):
                    with st.spinner("Analyzing requisition and matching vendors..."):
                        selected_req = requisitions[requisitions["id"] == selected_id].iloc[0]
                        matches = match_vendors_to_requisition(selected_req, vendors, get_openai_key())

                        if matches:
                            save_vendor_matches(selected_id, matches)
                            st.success(f"Successfully assigned {len(matches)} vendors to this requisition.")
                        else:
                            st.error("Could not find suitable vendors. Please try again.")
            else:
                st.warning("Please enter your OpenAI API key in the settings above to use auto-assignment.")

        with col2:
            if selected_id:
                selected_row = requisitions[requisitions["id"] == selected_id].iloc[0]

                st.markdown(f'<div class="subheader">🤝 Vendor Matches for Requisition #{selected_id}</div>',
                            unsafe_allow_html=True)

                # Show requisition details
                with st.expander("Requisition Details", expanded=True):
                    st.markdown(f"**Title:** {selected_row['title']}")
                    st.markdown(f"**Description:** {selected_row['description']}")
                    st.markdown(f"**Quantity:** {selected_row['quantity']} {selected_row['unit']}")
                    st.markdown(
                        f"**Request Date:** {pd.to_datetime(selected_row['request_date']).strftime('%Y-%m-%d')}")

                # Load and show vendor matches
                vendor_matches = load_requisition_vendors(selected_id)

                if vendor_matches.empty:
                    st.info(
                        "No vendors have been assigned to this requisition yet. Use 'Auto-Assign Vendors' to find suitable vendors.")
                else:
                    st.markdown(f"### {len(vendor_matches)} Vendor Matches")

                    for _, match in vendor_matches.iterrows():
                        # Create a formatted card for each vendor match
                        status_class = f"approval-{match['status']}"
                        match_score = int(match['match_score'] * 100)
                        match_score_display = f"<span class='match-score'>{match_score}% Match</span>"

                        st.markdown(f"""
                        <div class='vendor-match'>
                            <div class='vendor-match-title'>{match['vendor_name']} {match_score_display}</div>
                            <div><strong>Email:</strong> {match['vendor_email']}</div>
                            <div><strong>Status:</strong> <span class='{status_class}'>{match['status'].upper()}</span></div>
                            <div style='margin-top: 8px;'><strong>Match Reason:</strong> {match['match_reason']}</div>
                        </div>
                        """, unsafe_allow_html=True)

with tab2:
    st.markdown('<div class="subheader">✅ Approval Management</div>', unsafe_allow_html=True)

    # Load all pending vendor assignments
    pending_matches = pd.read_sql_query("""
        SELECT rv.*, 
               r.title as requisition_title,
               v.name as vendor_name,
               v.email as vendor_email,
               v.description as vendor_description
        FROM requisition_vendors rv
        JOIN requisitions r ON rv.requisition_id = r.id
        JOIN vendors v ON rv.vendor_id = v.id
        ORDER BY rv.created_at DESC
    """, conn)

    if pending_matches.empty:
        st.info("No vendor assignments to approve at this time.")
    else:
        # Create approval tabs
        approval_tabs = st.tabs(["All", "Pending", "Approved", "Rejected"])

        with approval_tabs[0]:  # All
            display_all(pending_matches)

        with approval_tabs[1]:  # Pending
            pending_only = pending_matches[pending_matches['status'] == 'pending']
            if pending_only.empty:
                st.info("No pending vendor assignments.")
            else:
                display_pending(pending_only)

        with approval_tabs[2]:  # Approved
            approved_only = pending_matches[pending_matches['status'] == 'approved']
            if approved_only.empty:
                st.info("No approved vendor assignments.")
            else:
                display_approved(approved_only)

        with approval_tabs[3]:  # Rejected
            rejected_only = pending_matches[pending_matches['status'] == 'rejected']
            if rejected_only.empty:
                st.info("No rejected vendor assignments.")
            else:
                display_rejected(rejected_only)


# Helper functions for displaying approval tabs
def display_all(matches):
    st.markdown("### All Vendor Assignments")

    # Format for display
    display_df = matches.copy()
    display_df['match_score'] = (display_df['match_score'] * 100).round().astype(int).astype(str) + "%"
    display_df['created_at'] = pd.to_datetime(display_df['created_at']).dt.strftime("%Y-%m-%d %H:%M")
    display_df['approved_at'] = pd.to_datetime(display_df['approved_at']).apply(
        lambda x: x.strftime("%Y-%m-%d %H:%M") if not pd.isna(x) else ""
    )

    # Show the dataframe
    st.dataframe(
        display_df[[
            'id', 'requisition_id', 'requisition_title',
            'vendor_id', 'vendor_name', 'match_score',
            'status', 'created_at', 'approved_at'
        ]],
        use_container_width=True,
        height=400
    )

    # Allow choosing a match to see details
    selected_match_id = st.selectbox(
        "Select a vendor assignment to view details",
        matches['id'],
        format_func=lambda
            x: f"Match #{x}: {matches[matches['id'] == x].iloc[0]['vendor_name']} for {matches[matches['id'] == x].iloc[0]['requisition_title']}"
    )

    if selected_match_id:
        display_match_details(matches[matches['id'] == selected_match_id].iloc[0])


def display_pending(matches):
    st.markdown("### Pending Vendor Assignments")

    # Initialize session state for approval actions if not already done
    if "pending_actions" not in st.session_state:
        st.session_state.pending_actions = {}

    for _, match in matches.iterrows():
        match_id = match['id']
        match_score = int(match['match_score'] * 100)

        # Create unique keys for this match
        approve_key = f"approve_{match_id}"
        reject_key = f"reject_{match_id}"

        # Initialize if not present in session state
        if match_id not in st.session_state.pending_actions:
            st.session_state.pending_actions[match_id] = {
                "approved": False,
                "rejected": False
            }

        # Display match details
        st.markdown(f"""
        <div class='vendor-match'>
            <div class='vendor-match-title'>
                REQ-{match['requisition_id']:04d}: {match['requisition_title']} → {match['vendor_name']}
                <span class='match-score'>{match_score}% Match</span>
            </div>
            <div><strong>Match Reason:</strong> {match['match_reason']}</div>
            <div style='margin-top:5px;'><strong>Created:</strong> {pd.to_datetime(match['created_at']).strftime('%Y-%m-%d %H:%M')}</div>
        </div>
        """, unsafe_allow_html=True)

        # Check if this match has already been acted upon
        if st.session_state.pending_actions[match_id]["approved"]:
            st.success(f"Vendor match #{match_id} approved successfully!")
        elif st.session_state.pending_actions[match_id]["rejected"]:
            st.warning(f"Vendor match #{match_id} rejected.")
        else:
            # Show action buttons if no action taken yet
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"✅ Approve", key=approve_key):
                    update_vendor_match_status(match_id, "approved")
                    st.session_state.pending_actions[match_id]["approved"] = True
                    st.rerun()
            with col2:
                if st.button(f"❌ Reject", key=reject_key):
                    update_vendor_match_status(match_id, "rejected")
                    st.session_state.pending_actions[match_id]["rejected"] = True
                    st.rerun()

        st.markdown("---")

def display_approved(matches):
    st.markdown("### Approved Vendor Assignments")

    for _, match in matches.iterrows():
        match_id = match['id']
        match_score = int(match['match_score'] * 100)

        st.markdown(f"""
        <div class='vendor-match'>
            <div class='vendor-match-title'>
                REQ-{match['requisition_id']:04d}: {match['requisition_title']} → {match['vendor_name']}
                <span class='match-score'>{match_score}% Match</span>
                <span class='approval-approved' style='padding:3px 8px;border-radius:4px;margin-left:10px;'>APPROVED</span>
            </div>
            <div><strong>Match Reason:</strong> {match['match_reason']}</div>
            <div style='margin-top:5px;'>
                <strong>Created:</strong> {pd.to_datetime(match['created_at']).strftime('%Y-%m-%d %H:%M')} | 
                <strong>Approved:</strong> {pd.to_datetime(match['approved_at']).strftime('%Y-%m-%d %H:%M')}
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button(f"❌ Revoke Approval", key=f"revoke_{match_id}"):
            update_vendor_match_status(match_id, "pending")
            st.success(f"Approval revoked. Vendor match #{match_id} is now pending.")
            st.rerun()

        st.markdown("---")


def display_rejected(matches):
    st.markdown("### Rejected Vendor Assignments")

    for _, match in matches.iterrows():
        match_id = match['id']
        match_score = int(match['match_score'] * 100)

        st.markdown(f"""
        <div class='vendor-match'>
            <div class='vendor-match-title'>
                REQ-{match['requisition_id']:04d}: {match['requisition_title']} → {match['vendor_name']}
                <span class='match-score'>{match_score}% Match</span>
                <span class='approval-rejected' style='padding:3px 8px;border-radius:4px;margin-left:10px;'>REJECTED</span>
            </div>
            <div><strong>Match Reason:</strong> {match['match_reason']}</div>
            <div style='margin-top:5px;'>
                <strong>Created:</strong> {pd.to_datetime(match['created_at']).strftime('%Y-%m-%d %H:%M')} | 
                <strong>Rejected:</strong> {pd.to_datetime(match['approved_at']).strftime('%Y-%m-%d %H:%M')}
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button(f"🔄 Reconsider", key=f"reconsider_{match_id}"):
            update_vendor_match_status(match_id, "pending")
            st.success(f"Vendor match #{match_id} returned to pending status.")
            st.rerun()

        st.markdown("---")


def display_match_details(match):
    st.markdown(f"### Match Details #{match['id']}")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Requisition Details")
        st.markdown(f"**ID:** REQ-{match['requisition_id']:04d}")
        st.markdown(f"**Title:** {match['requisition_title']}")

    with col2:
        st.markdown("#### Vendor Details")
        st.markdown(f"**ID:** {match['vendor_id']}")
        st.markdown(f"**Name:** {match['vendor_name']}")
        st.markdown(f"**Email:** {match['vendor_email']}")

    st.markdown("#### Match Information")
    st.markdown(f"**Match Score:** {int(match['match_score'] * 100)}%")
    st.markdown(f"**Match Reason:** {match['match_reason']}")
    st.markdown(f"**Status:** {match['status'].upper()}")
    st.markdown(f"**Created:** {pd.to_datetime(match['created_at']).strftime('%Y-%m-%d %H:%M')}")

    if match['approved_at']:
        st.markdown(f"**Decision Date:** {pd.to_datetime(match['approved_at']).strftime('%Y-%m-%d %H:%M')}")

    st.markdown("#### Actions")
    col1, col2, col3 = st.columns(3)

    with col1:
        if match['status'] != "approved":
            if st.button("✅ Approve", key=f"detail_approve_{match['id']}"):
                update_vendor_match_status(match['id'], "approved")
                st.success(f"Vendor match #{match['id']} approved successfully!")
                st.rerun()

    with col2:
        if match['status'] != "pending":
            if st.button("🔄 Set Pending", key=f"detail_pending_{match['id']}"):
                update_vendor_match_status(match['id'], "pending")
                st.success(f"Vendor match #{match['id']} set to pending.")
                st.rerun()

    with col3:
        if match['status'] != "rejected":
            if st.button("❌ Reject", key=f"detail_reject_{match['id']}"):
                update_vendor_match_status(match['id'], "rejected")
                st.success(f"Vendor match #{match['id']} rejected.")
                st.rerun()