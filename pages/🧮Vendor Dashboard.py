import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import json

# Page configuration
st.set_page_config(
    page_title="💰 Vendor Bidding Portal",
    page_icon="💰",
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
    .success {
        background-color: #D1FAE5;
        padding: 15px;
        border-radius: 5px;
        color: #065F46;
        font-weight: bold;
        margin: 10px 0;
    }
    .bid-card {
        border-left: 4px solid #2563EB;
        background-color: #F9FAFB;
        padding: 15px;
        margin: 10px 0;
        border-radius: 0 5px 5px 0;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    .bid-submitted {
        border-left: 4px solid #059669;
    }
    .bid-badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .bid-pending {
        background-color: #FEF3C7;
        color: #92400E;
    }
    .bid-submitted {
        background-color: #D1FAE5;
        color: #065F46;
    }
    .price-highlight {
        font-size: 1.2rem;
        font-weight: bold;
        color: #1E3A8A;
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
st.markdown('<div class="main-header">💰 Vendor Bidding Portal</div>', unsafe_allow_html=True)
st.markdown('<p class="info-text">Submit and manage your bids for assigned requisitions</p>', unsafe_allow_html=True)


# Initialize database connection
@st.cache_resource
def init_db_connection():
    conn = sqlite3.connect('db.db', check_same_thread=False)

    # Create vendor_bids table if it doesn't exist
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vendor_bids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER,
            requisition_id INTEGER,
            bid_amount REAL,
            currency TEXT DEFAULT 'USD',
            notes TEXT,
            delivery_time INTEGER,
            delivery_unit TEXT DEFAULT 'days',
            bid_timestamp TEXT,
            status TEXT DEFAULT 'submitted',
            FOREIGN KEY (vendor_id) REFERENCES vendors (id),
            FOREIGN KEY (requisition_id) REFERENCES requisitions (id)
        )
    """)

    conn.commit()
    return conn


conn = init_db_connection()


# Database functions
def load_vendors():
    df = pd.read_sql_query("SELECT * FROM vendors ORDER BY name", conn)
    return df


def load_vendor_requisitions(vendor_id):
    # Get requisitions assigned to this vendor
    df = pd.read_sql_query("""
        SELECT rv.*, r.title, r.description, r.quantity, r.unit, r.request_date
        FROM requisition_vendors rv
        JOIN requisitions r ON rv.requisition_id = r.id
        WHERE rv.vendor_id = ? AND rv.status = 'approved'
        ORDER BY rv.created_at DESC
    """, conn, params=(vendor_id,))
    return df


def load_vendor_bids(vendor_id):
    # Get all bids submitted by this vendor
    df = pd.read_sql_query("""
        SELECT vb.*, r.title as requisition_title
        FROM vendor_bids vb
        JOIN requisitions r ON vb.requisition_id = r.id
        WHERE vb.vendor_id = ?
        ORDER BY vb.bid_timestamp DESC
    """, conn, params=(vendor_id,))
    return df


def check_existing_bid(vendor_id, requisition_id):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM vendor_bids WHERE vendor_id = ? AND requisition_id = ?",
        (vendor_id, requisition_id)
    )
    result = cursor.fetchone()
    return result[0] if result else None


def save_bid(vendor_id, requisition_id, bid_amount, currency, notes, delivery_time, delivery_unit):
    cursor = conn.cursor()
    bid_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Check if bid already exists
    existing_bid_id = check_existing_bid(vendor_id, requisition_id)

    if existing_bid_id:
        # Update existing bid
        cursor.execute(
            """
            UPDATE vendor_bids 
            SET bid_amount = ?, currency = ?, notes = ?, 
                delivery_time = ?, delivery_unit = ?, 
                bid_timestamp = ?, status = 'updated'
            WHERE id = ?
            """,
            (bid_amount, currency, notes, delivery_time, delivery_unit, bid_timestamp, existing_bid_id)
        )
    else:
        # Insert new bid
        cursor.execute(
            """
            INSERT INTO vendor_bids 
            (vendor_id, requisition_id, bid_amount, currency, notes, delivery_time, delivery_unit, bid_timestamp, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'submitted')
            """,
            (vendor_id, requisition_id, bid_amount, currency, notes, delivery_time, delivery_unit, bid_timestamp)
        )

    conn.commit()
    return True


# Vendor login (simplified for demo)
def vendor_login():
    if "vendor_id" not in st.session_state:
        st.session_state.vendor_id = None
        st.session_state.vendor_name = None

    vendors = load_vendors()

    if vendors.empty:
        st.error("No vendors found in the system. Please contact the administrator.")
        return False

    with st.form("vendor_login_form"):
        st.subheader("Vendor Login")
        vendor_select = st.selectbox(
            "Select your vendor account:",
            vendors["id"],
            format_func=lambda
                x: f"{vendors[vendors['id'] == x].iloc[0]['name']} ({vendors[vendors['id'] == x].iloc[0]['email']})"
        )

        submitted = st.form_submit_button("Login")

        if submitted:
            st.session_state.vendor_id = vendor_select
            st.session_state.vendor_name = vendors[vendors["id"] == vendor_select].iloc[0]["name"]
            st.success(f"Welcome, {st.session_state.vendor_name}!")
            return True

    return False


# Main app
if "vendor_id" in st.session_state and st.session_state.vendor_id:
    # Vendor is logged in
    vendor_id = st.session_state.vendor_id
    vendor_name = st.session_state.vendor_name

    # Show vendor info
    st.sidebar.markdown(f"**Logged in as:** {vendor_name}")
    if st.sidebar.button("Logout"):
        st.session_state.vendor_id = None
        st.session_state.vendor_name = None
        st.rerun()

    # Main tabs
    tab1, tab2 = st.tabs(["📋 Available Requisitions", "📜 My Bids"])

    with tab1:
        st.markdown('<div class="subheader">📋 Requisitions Assigned to You</div>', unsafe_allow_html=True)

        # Load requisitions assigned to this vendor
        vendor_requisitions = load_vendor_requisitions(vendor_id)

        if vendor_requisitions.empty:
            st.info("No requisitions have been assigned to you yet.")
        else:
            # Check for existing bids
            vendor_bids = load_vendor_bids(vendor_id)
            bid_map = {}
            if not vendor_bids.empty:
                for _, bid in vendor_bids.iterrows():
                    bid_map[bid["requisition_id"]] = {
                        "amount": bid["bid_amount"],
                        "currency": bid["currency"],
                        "delivery": f"{bid['delivery_time']} {bid['delivery_unit']}",
                        "notes": bid["notes"],
                        "timestamp": bid["bid_timestamp"]
                    }

            # Display requisitions with bidding options
            for _, req in vendor_requisitions.iterrows():
                # Determine if bid exists
                has_bid = req["requisition_id"] in bid_map
                card_class = "bid-card bid-submitted" if has_bid else "bid-card"

                st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)

                # Show requisition details
                st.markdown(f"### REQ-{req['requisition_id']:04d}: {req['title']}")

                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**Description:** {req['description']}")
                    st.markdown(f"**Quantity:** {req['quantity']} {req['unit']}")
                    st.markdown(f"**Request Date:** {pd.to_datetime(req['request_date']).strftime('%Y-%m-%d')}")

                with col2:
                    match_score = int(req['match_score'] * 100)
                    st.markdown(f"**Match Score:** {match_score}%")

                    status_badge = "bid-submitted" if has_bid else "bid-pending"
                    status_text = "Bid Submitted" if has_bid else "Awaiting Bid"
                    st.markdown(f'<span class="bid-badge {status_badge}">{status_text}</span>', unsafe_allow_html=True)

                    if has_bid:
                        st.markdown(f"""
                        <div style='margin-top:10px;'>
                            <strong>Your Bid:</strong> <span class='price-highlight'>{bid_map[req['requisition_id']]['amount']} {bid_map[req['requisition_id']]['currency']}</span>
                        </div>
                        <div>
                            <strong>Delivery:</strong> {bid_map[req['requisition_id']]['delivery']}
                        </div>
                        <div style='margin-top:5px; font-size:0.8rem;'>
                            Submitted: {pd.to_datetime(bid_map[req['requisition_id']]['timestamp']).strftime('%Y-%m-%d %H:%M')}
                        </div>
                        """, unsafe_allow_html=True)

                # Bid form
                with st.expander("Submit Bid" if not has_bid else "Update Bid", expanded=not has_bid):
                    with st.form(key=f"bid_form_{req['requisition_id']}"):
                        st.markdown(
                            f"### {'Submit' if not has_bid else 'Update'} Bid for REQ-{req['requisition_id']:04d}")

                        col1, col2 = st.columns(2)
                        with col1:
                            bid_amount = st.number_input(
                                "Bid Amount:",
                                min_value=0.01,
                                value=float(bid_map[req['requisition_id']]['amount']) if has_bid else 100.00,
                                step=0.01
                            )

                        with col2:
                            currency = st.selectbox(
                                "Currency:",
                                ["USD", "EUR", "GBP", "JPY", "CAD", "AUD"],
                                index=["USD", "EUR", "GBP", "JPY", "CAD", "AUD"].index(
                                    bid_map[req['requisition_id']]['currency']) if has_bid else 0
                            )

                        col1, col2 = st.columns(2)
                        with col1:
                            delivery_time = st.number_input(
                                "Delivery Time:",
                                min_value=1,
                                value=int(bid_map[req['requisition_id']]['delivery'].split()[0]) if has_bid else 14,
                                step=1
                            )

                        with col2:
                            delivery_unit = st.selectbox(
                                "Delivery Unit:",
                                ["days", "weeks", "months"],
                                index=["days", "weeks", "months"].index(
                                    bid_map[req['requisition_id']]['delivery'].split()[1]) if has_bid and bid_map[
                                    req['requisition_id']]['delivery'].split()[1] in ["days", "weeks", "months"] else 0
                            )

                        notes = st.text_area(
                            "Additional Notes:",
                            value=bid_map[req['requisition_id']]['notes'] if has_bid else "",
                            placeholder="Add any details about your bid, such as payment terms, delivery conditions, etc."
                        )

                        st.markdown('<div class="success-button">', unsafe_allow_html=True)
                        submitted = st.form_submit_button("Submit Bid" if not has_bid else "Update Bid")
                        st.markdown('</div>', unsafe_allow_html=True)

                        if submitted:
                            success = save_bid(
                                vendor_id,
                                req['requisition_id'],
                                bid_amount,
                                currency,
                                notes,
                                delivery_time,
                                delivery_unit
                            )

                            if success:
                                st.success(
                                    f"Your bid has been {'submitted' if not has_bid else 'updated'} successfully!")
                                st.rerun()

                st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="subheader">📜 My Bid History</div>', unsafe_allow_html=True)

        # Load all bids from this vendor
        vendor_bids = load_vendor_bids(vendor_id)

        if vendor_bids.empty:
            st.info("You haven't submitted any bids yet.")
        else:
            # Format for display
            display_df = vendor_bids.copy()
            display_df["bid_timestamp"] = pd.to_datetime(display_df["bid_timestamp"]).dt.strftime("%Y-%m-%d %H:%M")
            display_df["bid_display"] = display_df.apply(lambda row: f"{row['bid_amount']} {row['currency']}", axis=1)
            display_df["delivery_display"] = display_df.apply(
                lambda row: f"{row['delivery_time']} {row['delivery_unit']}", axis=1)

            # Show bids table
            st.dataframe(
                display_df[
                    ["id", "requisition_title", "bid_display", "delivery_display", "status", "bid_timestamp"]].rename(
                    columns={
                        "id": "Bid ID",
                        "requisition_title": "Requisition",
                        "bid_display": "Amount",
                        "delivery_display": "Delivery Time",
                        "status": "Status",
                        "bid_timestamp": "Submitted On"
                    }
                ),
                use_container_width=True,
                height=300
            )

            # Bid details
            selected_bid_id = st.selectbox(
                "Select a bid to view details",
                vendor_bids["id"],
                format_func=lambda x: f"Bid #{x} for {vendor_bids[vendor_bids['id'] == x].iloc[0]['requisition_title']}"
            )

            if selected_bid_id:
                selected_bid = vendor_bids[vendor_bids["id"] == selected_bid_id].iloc[0]

                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown(f"### Bid #{selected_bid_id} Details")

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Requisition:** {selected_bid['requisition_title']}")
                    st.markdown(f"**Bid Amount:** {selected_bid['bid_amount']} {selected_bid['currency']}")
                    st.markdown(f"**Delivery Time:** {selected_bid['delivery_time']} {selected_bid['delivery_unit']}")

                with col2:
                    st.markdown(f"**Status:** {selected_bid['status'].upper()}")
                    st.markdown(
                        f"**Submitted On:** {pd.to_datetime(selected_bid['bid_timestamp']).strftime('%Y-%m-%d %H:%M')}")

                if selected_bid['notes']:
                    st.markdown("**Additional Notes:**")
                    st.info(selected_bid['notes'])

                st.markdown('</div>', unsafe_allow_html=True)
else:
    # Show login screen
    vendor_login()