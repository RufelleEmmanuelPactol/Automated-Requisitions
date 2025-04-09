import sqlite3
import streamlit as st

# Initialize DB
def init():
    conn = sqlite3.connect('db.db', check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            description TEXT
        )
    """)
    return conn

conn = init()

# Helper functions
def add_vendor(name, email, description):
    conn.execute("INSERT INTO vendors (name, email, description) VALUES (?, ?, ?)", (name, email, description))
    conn.commit()

def get_vendors():
    return conn.execute("SELECT * FROM vendors").fetchall()

def update_vendor(vendor_id, name, email, description):
    conn.execute("UPDATE vendors SET name = ?, email = ?, description = ? WHERE id = ?", (name, email, description, vendor_id))
    conn.commit()

def delete_vendor(vendor_id):
    conn.execute("DELETE FROM vendors WHERE id = ?", (vendor_id,))
    conn.commit()

# Streamlit UI
st.title("🛠️ Vendor Management")

# Section to add new vendor
with st.expander("➕ Add New Vendor"):
    name = st.text_input("Vendor Name")
    email = st.text_input("Vendor Email")
    description = st.text_area("Description")
    if st.button("Add Vendor"):
        if name and email:
            add_vendor(name, email, description)
            st.success(f"Vendor '{name}' added.")
        else:
            st.warning("Name and Email are required.")

# Show vendor list
st.subheader("📋 Existing Vendors")

vendors = get_vendors()

for v in vendors:
    with st.expander(f"{v[1]}"):
        new_name = st.text_input(f"Name [{v[0]}]", value=v[1], key=f"name_{v[0]}")
        new_email = st.text_input(f"Email [{v[0]}]", value=v[2], key=f"email_{v[0]}")
        new_desc = st.text_area(f"Description [{v[0]}]", value=v[3], key=f"desc_{v[0]}")

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Update", key=f"update_{v[0]}"):
                update_vendor(v[0], new_name, new_email, new_desc)
                st.success(f"Vendor '{new_name}' updated.")
        with col2:
            if st.button("Delete", key=f"delete_{v[0]}"):
                delete_vendor(v[0])
                st.warning(f"Vendor '{v[1]}' deleted.")
                st.rerun()