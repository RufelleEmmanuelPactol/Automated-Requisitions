import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import json

# Page configuration
st.set_page_config(
    page_title="🔍 Bid Approval System",
    page_icon="🔍",
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
    .success-button>button {
        background-color: #059669;
    }
    .success-button>button:hover {
        background-color: #047857;
    }
    .danger-button>button {
        background-color: #DC2626;
        color: white;
    }
    .danger-button>button:hover {
        background-color: #B91C1C;
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
    .tier-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: bold;
        text-transform: uppercase;
        margin-bottom: 10px;
    }
    .tier-1 {
        background-color: #D1FAE5;
        color: #065F46;
    }
    .tier-2 {
        background-color: #E0F2FE;
        color: #075985;
    }
    .tier-3 {
        background-color: #FEF3C7;
        color: #92400E;
    }
    .tier-4 {
        background-color: #FEE2E2;
        color: #B91C1C;
    }
    .price-tag {
        font-size: 1.5rem;
        font-weight: bold;
        color: #1E3A8A;
        margin: 10px 0;
    }
    .bid-card {
        border-left: 4px solid #3B82F6;
        background-color: #F9FAFB;
        padding: 15px;
        margin: 10px 0;
        border-radius: 0 5px 5px 0;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    .status-badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: bold;
        text-transform: uppercase;
    }
    .status-pending {
        background-color: #E0F2FE;
        color: #075985;
    }
    .status-approved {
        background-color: #D1FAE5;
        color: #065F46;
    }
    .status-rejected {
        background-color: #FEE2E2;
        color: #B91C1C;
    }
    .comparison-table {
        width: 100%;
        border-collapse: collapse;
        margin: 15px 0;
    }
    .comparison-table th {
        background-color: #E0F2FE;
        padding: 8px;
        text-align: left;
        border: 1px solid #CBD5E1;
    }
    .comparison-table td {
        padding: 8px;
        border: 1px solid #CBD5E1;
    }
    .comparison-table tr:nth-child(even) {
        background-color: #F8FAFC;
    }
    .comparison-table .best-value {
        background-color: #D1FAE5;
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
st.markdown('<div class="main-header">🔍 Bid Approval System</div>', unsafe_allow_html=True)
st.markdown('<p class="info-text">Review and approve vendor bids based on tiered approval thresholds</p>',
            unsafe_allow_html=True)


# Initialize database connection
@st.cache_resource
def init_db_connection():
    conn = sqlite3.connect('db.db', check_same_thread=False)

    # Create bid_approvals table if it doesn't exist
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bid_approvals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            requisition_id INTEGER,
            vendor_bid_id INTEGER,
            approval_tier TEXT,
            approved_by TEXT,
            approved_at TEXT,
            approval_notes TEXT,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (requisition_id) REFERENCES requisitions (id),
            FOREIGN KEY (vendor_bid_id) REFERENCES vendor_bids (id)
        )
    """)

    conn.commit()
    return conn


conn = init_db_connection()

# Approval tiers definition
APPROVAL_TIERS = [
    {"name": "Department Manager", "min": 0, "max": 5000, "level": 1, "class": "tier-1"},
    {"name": "Division Director", "min": 5000, "max": 25000, "level": 2, "class": "tier-2"},
    {"name": "VP Level", "min": 25000, "max": 100000, "level": 3, "class": "tier-3"},
    {"name": "C-Suite", "min": 100000, "max": float('inf'), "level": 4, "class": "tier-4"}
]


# Helper function to determine approval tier
def get_approval_tier(amount):
    for tier in APPROVAL_TIERS:
        if tier["min"] <= amount < tier["max"]:
            return tier
    return APPROVAL_TIERS[-1]  # Default to highest tier if not found


# Database functions
def load_requisitions_with_bids():
    df = pd.read_sql_query("""
        SELECT r.id as requisition_id, r.title, r.description, r.quantity, r.unit,
               COUNT(vb.id) as bid_count,
               MIN(vb.bid_amount) as min_bid,
               MAX(vb.bid_amount) as max_bid,
               AVG(vb.bid_amount) as avg_bid,
               (SELECT vb2.currency FROM vendor_bids vb2 WHERE vb2.requisition_id = r.id LIMIT 1) as currency
        FROM requisitions r
        JOIN vendor_bids vb ON r.id = vb.requisition_id
        GROUP BY r.id
        ORDER BY r.id DESC
    """, conn)
    return df


def load_bids_for_requisition(requisition_id):
    df = pd.read_sql_query("""
        SELECT vb.*, v.name as vendor_name, v.email as vendor_email,
               ba.status as approval_status, ba.approved_by, ba.approved_at, ba.approval_notes
        FROM vendor_bids vb
        JOIN vendors v ON vb.vendor_id = v.id
        LEFT JOIN bid_approvals ba ON vb.id = ba.vendor_bid_id
        WHERE vb.requisition_id = ?
        ORDER BY vb.bid_amount ASC
    """, conn, params=(requisition_id,))
    return df


def get_requisition_details(requisition_id):
    df = pd.read_sql_query("""
        SELECT * FROM requisitions WHERE id = ?
    """, conn, params=(requisition_id,))
    if df.empty:
        return None
    return df.iloc[0]


def get_bid_details(bid_id):
    df = pd.read_sql_query("""
        SELECT vb.*, v.name as vendor_name, v.email as vendor_email
        FROM vendor_bids vb
        JOIN vendors v ON vb.vendor_id = v.id
        WHERE vb.id = ?
    """, conn, params=(bid_id,))
    if df.empty:
        return None
    return df.iloc[0]


def approve_bid(bid_id, requisition_id, approver, notes, tier_name):
    cursor = conn.cursor()
    approval_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Check if approval already exists
    cursor.execute(
        "SELECT id FROM bid_approvals WHERE vendor_bid_id = ?",
        (bid_id,)
    )
    result = cursor.fetchone()

    if result:
        # Update existing approval
        cursor.execute(
            """
            UPDATE bid_approvals 
            SET approval_tier = ?, approved_by = ?, approved_at = ?, 
                approval_notes = ?, status = 'approved'
            WHERE vendor_bid_id = ?
            """,
            (tier_name, approver, approval_time, notes, bid_id)
        )
    else:
        # Insert new approval
        cursor.execute(
            """
            INSERT INTO bid_approvals 
            (requisition_id, vendor_bid_id, approval_tier, approved_by, approved_at, approval_notes, status)
            VALUES (?, ?, ?, ?, ?, ?, 'approved')
            """,
            (requisition_id, bid_id, tier_name, approver, approval_time, notes)
        )

    # Mark other bids as rejected
    cursor.execute(
        """
        INSERT OR REPLACE INTO bid_approvals 
        (requisition_id, vendor_bid_id, approval_tier, approved_by, approved_at, approval_notes, status)
        SELECT ?, id, ?, ?, ?, 'Automatically rejected as another bid was selected', 'rejected'
        FROM vendor_bids
        WHERE requisition_id = ? AND id != ?
        """,
        (requisition_id, tier_name, approver, approval_time, requisition_id, bid_id)
    )

    conn.commit()
    return True


def reject_bid(bid_id, requisition_id, approver, notes, tier_name):
    cursor = conn.cursor()
    approval_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Check if approval already exists
    cursor.execute(
        "SELECT id FROM bid_approvals WHERE vendor_bid_id = ?",
        (bid_id,)
    )
    result = cursor.fetchone()

    if result:
        # Update existing approval
        cursor.execute(
            """
            UPDATE bid_approvals 
            SET approval_tier = ?, approved_by = ?, approved_at = ?, 
                approval_notes = ?, status = 'rejected'
            WHERE vendor_bid_id = ?
            """,
            (tier_name, approver, approval_time, notes, bid_id)
        )
    else:
        # Insert new approval
        cursor.execute(
            """
            INSERT INTO bid_approvals 
            (requisition_id, vendor_bid_id, approval_tier, approved_by, approved_at, approval_notes, status)
            VALUES (?, ?, ?, ?, ?, ?, 'rejected')
            """,
            (requisition_id, bid_id, tier_name, approver, approval_time, notes)
        )

    conn.commit()
    return True


# Initialize session state for approvals if not already done
if "bid_approvals" not in st.session_state:
    st.session_state.bid_approvals = {}

# Main layout
tab1, tab2 = st.tabs(["📦 Requisitions with Bids", "📊 Approval Dashboard"])

with tab1:
    st.markdown('<div class="subheader">📦 Requisitions with Vendor Bids</div>', unsafe_allow_html=True)

    # Load requisitions with submitted bids
    requisitions_with_bids = load_requisitions_with_bids()

    if requisitions_with_bids.empty:
        st.info("No requisitions with submitted bids found.")
    else:
        # Format the dataframe for display
        display_df = requisitions_with_bids.copy()

        # Add price range column
        display_df["price_range"] = display_df.apply(
            lambda row: f"{row['currency']} {row['min_bid']} - {row['currency']} {row['max_bid']}", axis=1
        )

        # Determine approval tier for each requisition based on max bid
        display_df["approval_tier"] = display_df.apply(
            lambda row: get_approval_tier(row["max_bid"])["name"], axis=1
        )

        # Show the requisitions table
        st.dataframe(
            display_df[["requisition_id", "title", "bid_count", "price_range", "approval_tier"]].rename(
                columns={
                    "requisition_id": "ID",
                    "title": "Requisition Title",
                    "bid_count": "# of Bids",
                    "price_range": "Price Range",
                    "approval_tier": "Required Approval"
                }
            ),
            use_container_width=True,
            height=300
        )

        # Select a requisition to review
        selected_req_id = st.selectbox(
            "Select a requisition to review bids",
            requisitions_with_bids["requisition_id"],
            format_func=lambda
                x: f"REQ-{x:04d}: {requisitions_with_bids[requisitions_with_bids['requisition_id'] == x].iloc[0]['title']}"
        )

        if selected_req_id:
            # Get requisition details
            req_details = get_requisition_details(selected_req_id)

            # Get all bids for this requisition
            bids = load_bids_for_requisition(selected_req_id)

            if bids.empty:
                st.warning(f"No bids found for requisition #{selected_req_id}.")
            else:
                # Determine the highest bid amount for tier calculation
                max_bid = bids["bid_amount"].max()
                approval_tier = get_approval_tier(max_bid)

                # Display requisition header with approval tier
                st.markdown(f"""
                <div class="card">
                    <h3>REQ-{selected_req_id:04d}: {req_details['title']}</h3>
                    <div class="tier-badge {approval_tier['class']}">
                        {approval_tier['name']} Approval Required
                    </div>
                    <p><strong>Description:</strong> {req_details['description']}</p>
                    <p><strong>Quantity:</strong> {req_details['quantity']} {req_details['unit']}</p>
                    <p><strong>Bids received:</strong> {len(bids)}</p>
                    <div class="price-tag">Price Range: {bids.iloc[0]['currency']} {bids['bid_amount'].min()} - {bids['bid_amount'].max()}</div>
                </div>
                """, unsafe_allow_html=True)

                # Create comparison table of all bids
                st.markdown("### Bid Comparison")

                # Find the best value (lowest bid)
                lowest_bid_id = bids.loc[bids['bid_amount'].idxmin()]['id']

                # Start markdown table
                comparison_table_md = "| Vendor | Bid Amount | Delivery Time | Status |\n"
                comparison_table_md += "|--------|------------|---------------|--------|\n"

                # Add rows
                for _, bid in bids.iterrows():
                    # Determine if this is the best value (add * for emphasis maybe)
                    vendor_name = f"**{bid['vendor_name']}**" if bid['id'] == lowest_bid_id else bid['vendor_name']

                    # Get status
                    status = bid['approval_status'] if not pd.isna(bid['approval_status']) else "pending"
                    status_text = status.upper()

                    # Add row to markdown
                    comparison_table_md += f"| {vendor_name} | {bid['currency']} {bid['bid_amount']} | {bid['delivery_time']} {bid['delivery_unit']} | {status_text} |\n"

                # Display table
                st.markdown(comparison_table_md, unsafe_allow_html=True)

                # Select a bid to approve
                st.markdown("### Review and Approve Bid")

                selected_bid_id = st.selectbox(
                    "Select a bid to review",
                    bids["id"],
                    format_func=lambda
                        x: f"{bids[bids['id'] == x].iloc[0]['vendor_name']}: {bids[bids['id'] == x].iloc[0]['currency']} {bids[bids['id'] == x].iloc[0]['bid_amount']}"
                )

                if selected_bid_id:
                    selected_bid = bids[bids["id"] == selected_bid_id].iloc[0]

                    # Check if already approved/rejected
                    if not pd.isna(selected_bid['approval_status']):
                        if selected_bid['approval_status'] == 'approved':
                            st.success(f"""
                            Bid from {selected_bid['vendor_name']} was APPROVED on {pd.to_datetime(selected_bid['approved_at']).strftime('%Y-%m-%d %H:%M')}.
                            Approved by: {selected_bid['approved_by']}
                            Notes: {selected_bid['approval_notes']}
                            """)
                        elif selected_bid['approval_status'] == 'rejected':
                            st.error(f"""
                            Bid from {selected_bid['vendor_name']} was REJECTED on {pd.to_datetime(selected_bid['approved_at']).strftime('%Y-%m-%d %H:%M')}.
                            Rejected by: {selected_bid['approved_by']}
                            Notes: {selected_bid['approval_notes']}
                            """)
                    else:
                        # Show approval form
                        with st.form(key=f"approval_form_{selected_bid_id}"):
                            st.markdown(f"### Review Bid from {selected_bid['vendor_name']}")

                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f"**Bid Amount:** {selected_bid['currency']} {selected_bid['bid_amount']}")
                                st.markdown(
                                    f"**Delivery:** {selected_bid['delivery_time']} {selected_bid['delivery_unit']}")

                            with col2:
                                st.markdown(f"**Required Approver:** {approval_tier['name']}")
                                st.markdown(f"**Tier Level:** {approval_tier['level']}")

                            approver_name = st.text_input(
                                "Your Name:",
                                placeholder="Enter your name as the approver"
                            )

                            approval_notes = st.text_area(
                                "Approval Notes:",
                                placeholder="Add any notes about this bid approval"
                            )

                            # Create row for buttons
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown('<div class="success-button">', unsafe_allow_html=True)
                                approve_button = st.form_submit_button("✅ Approve Bid")
                                st.markdown('</div>', unsafe_allow_html=True)

                            with col2:
                                st.markdown('<div class="danger-button">', unsafe_allow_html=True)
                                reject_button = st.form_submit_button("❌ Reject Bid")
                                st.markdown('</div>', unsafe_allow_html=True)

                            # Handle form submission
                            if approve_button or reject_button:
                                # Initialize bid ID in session state if not already there
                                if selected_bid_id not in st.session_state.bid_approvals:
                                    st.session_state.bid_approvals[selected_bid_id] = {
                                        "action": None,
                                        "processed": False
                                    }

                                # Validate inputs
                                if not approver_name:
                                    st.error("Please enter your name as the approver.")
                                else:
                                    # Process approval or rejection
                                    if approve_button:
                                        st.session_state.bid_approvals[selected_bid_id]["action"] = "approve"
                                        st.session_state.bid_approvals[selected_bid_id]["approver"] = approver_name
                                        st.session_state.bid_approvals[selected_bid_id]["notes"] = approval_notes

                                        # Update database
                                        approve_bid(
                                            selected_bid_id,
                                            selected_req_id,
                                            approver_name,
                                            approval_notes,
                                            approval_tier['name']
                                        )
                                        st.session_state.bid_approvals[selected_bid_id]["processed"] = True
                                        st.rerun()

                                    elif reject_button:
                                        st.session_state.bid_approvals[selected_bid_id]["action"] = "reject"
                                        st.session_state.bid_approvals[selected_bid_id]["approver"] = approver_name
                                        st.session_state.bid_approvals[selected_bid_id]["notes"] = approval_notes

                                        # Update database
                                        reject_bid(
                                            selected_bid_id,
                                            selected_req_id,
                                            approver_name,
                                            approval_notes,
                                            approval_tier['name']
                                        )
                                        st.session_state.bid_approvals[selected_bid_id]["processed"] = True
                                        st.rerun()

                        # Show success/error message based on session state after form is processed
                        if selected_bid_id in st.session_state.bid_approvals and \
                                st.session_state.bid_approvals[selected_bid_id]["processed"]:
                            if st.session_state.bid_approvals[selected_bid_id]["action"] == "approve":
                                st.success(f"Bid from {selected_bid['vendor_name']} has been approved successfully!")
                            elif st.session_state.bid_approvals[selected_bid_id]["action"] == "reject":
                                st.error(f"Bid from {selected_bid['vendor_name']} has been rejected.")

                        # Show bid details if provided
                        if selected_bid['notes']:
                            st.markdown("### Vendor Notes")
                            st.info(selected_bid['notes'])

with tab2:
    st.markdown('<div class="subheader">📊 Approval Dashboard</div>', unsafe_allow_html=True)

    # Get approved and pending bids from database
    approved_bids = pd.read_sql_query("""
        SELECT ba.*, r.title as requisition_title, vb.bid_amount, vb.currency,
               v.name as vendor_name, v.email as vendor_email
        FROM bid_approvals ba
        JOIN requisitions r ON ba.requisition_id = r.id
        JOIN vendor_bids vb ON ba.vendor_bid_id = vb.id
        JOIN vendors v ON vb.vendor_id = v.id
        WHERE ba.status = 'approved'
        ORDER BY ba.approved_at DESC
    """, conn)

    pending_approvals = pd.read_sql_query("""
        SELECT r.id as requisition_id, r.title, 
               MAX(vb.bid_amount) as max_bid_amount,
               MIN(vb.bid_amount) as min_bid_amount,
               COUNT(vb.id) as bid_count,
               vb.currency
        FROM requisitions r
        JOIN vendor_bids vb ON r.id = vb.requisition_id
        LEFT JOIN bid_approvals ba ON vb.id = ba.vendor_bid_id
        WHERE ba.id IS NULL  -- No approval records exist
        GROUP BY r.id
        ORDER BY max_bid_amount DESC
    """, conn)

    # Show approval statistics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Approved Bids", len(approved_bids))

    with col2:
        dept_manager_count = len(approved_bids[approved_bids['approval_tier'] == 'Department Manager'])
        st.metric("Dept. Manager Approvals", dept_manager_count)

    with col3:
        dir_count = len(approved_bids[approved_bids['approval_tier'] == 'Division Director'])
        st.metric("Division Director Approvals", dir_count)

    with col4:
        vp_count = len(approved_bids[approved_bids['approval_tier'] == 'VP Level'])
        c_suite_count = len(approved_bids[approved_bids['approval_tier'] == 'C-Suite'])
        st.metric("VP/C-Suite Approvals", vp_count + c_suite_count)

    # Show pending approvals by tier
    st.markdown("### Pending Approvals by Tier")

    if pending_approvals.empty:
        st.info("No requisitions pending approval.")
    else:
        # Create tier containers
        tier_cols = st.columns(4)

        # Track requisitions by tier
        tier_requisitions = {
            "Department Manager": [],
            "Division Director": [],
            "VP Level": [],
            "C-Suite": []
        }

        # Sort requisitions into tiers
        for _, row in pending_approvals.iterrows():
            tier = get_approval_tier(row['max_bid_amount'])
            tier_requisitions[tier['name']].append({
                "id": row['requisition_id'],
                "title": row['title'],
                "max_amount": row['max_bid_amount'],
                "min_amount": row['min_bid_amount'],
                "currency": row['currency'],
                "bid_count": row['bid_count']
            })

        # Display by tier
        for i, (tier_name, tier_class) in enumerate([
            ("Department Manager", "tier-1"),
            ("Division Director", "tier-2"),
            ("VP Level", "tier-3"),
            ("C-Suite", "tier-4")
        ]):
            with tier_cols[i]:
                st.markdown(
                    f'<div class="tier-badge {tier_class}" style="width:100%; text-align:center;">{tier_name}</div>',
                    unsafe_allow_html=True)

                if not tier_requisitions[tier_name]:
                    st.info(f"No approvals needed")
                else:
                    for req in tier_requisitions[tier_name]:
                        st.markdown(f"""
                        <div class="bid-card">
                            <strong>REQ-{req['id']:04d}:</strong> {req['title'][:30]}...
                            <div>{req['currency']} {req['min_amount']} - {req['max_amount']}</div>
                            <div>{req['bid_count']} bids</div>
                        </div>
                        """, unsafe_allow_html=True)

    # Recent approvals
    st.markdown("### Recent Bid Approvals")

    if approved_bids.empty:
        st.info("No approved bids yet.")
    else:
        # Format for display
        display_approved = approved_bids.copy()
        display_approved["approved_at"] = pd.to_datetime(display_approved["approved_at"]).dt.strftime("%Y-%m-%d %H:%M")
        display_approved["bid_display"] = display_approved.apply(lambda row: f"{row['currency']} {row['bid_amount']}",
                                                                 axis=1)

        # Show table of recent approvals
        st.dataframe(
            display_approved[["requisition_title", "vendor_name", "bid_display", "approval_tier", "approved_by",
                              "approved_at"]].rename(
                columns={
                    "requisition_title": "Requisition",
                    "vendor_name": "Vendor",
                    "bid_display": "Amount",
                    "approval_tier": "Approval Tier",
                    "approved_by": "Approved By",
                    "approved_at": "Date"
                }
            ).head(10),
            use_container_width=True,
            height=300
        )