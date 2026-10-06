import streamlit as st
import sqlite3
import os
import urllib.parse
import pandas as pd
from datetime import datetime
import qrcode
from io import BytesIO

# ================= কনফিগারেশন =================
UPLOAD_FOLDER = "uploaded_photos"
PAYMENT_PROOFS = "payment_proofs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PAYMENT_PROOFS, exist_ok=True)

# আপনার তথ্য এখানে বসান:
STUDIO_UPI_ID = "9775917899@ybl"      # আপনার GPay/PhonePe UPI ID
STUDIO_WHATSAPP = "919775917899"         # আপনার WhatsApp নম্বর (91...)

# প্রতি সার্ভিসের দাম (টাকায়)
SERVICE_PRICES = {
    "পাসপোর্ট সাইজ ফটো (3.2 x 4 cm)": 8,
    "স্ট্যাম্প সাইজ ফটো": 40,
    "4R প্রিন্ট (4 x 6 ইঞ্চি)": 40,
    "A4 সাইজ ফ্রেম প্রিন্ট": 250,
    "আইডি কার্ড প্রিন্ট": 60
}

# ================= ডাটাবেস =================
def init_db():
    conn = sqlite3.connect("studio_orders.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            customer_name TEXT,
            phone TEXT,
            service_type TEXT,
            copies INTEGER,
            total_price INTEGER,
            payment_txn_id TEXT,
            payment_proof_path TEXT,
            instruction TEXT,
            file_path TEXT,
            status TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def insert_order(name, phone, service, copies, total_price, txn_id, proof_path, instruction, file_path):
    conn = sqlite3.connect("studio_orders.db")
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''
        INSERT INTO orders (date, customer_name, phone, service_type, copies, total_price, payment_txn_id, payment_proof_path, instruction, file_path, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (now, name, phone, service, copies, total_price, txn_id, proof_path, instruction, file_path, 'Paid - Pending Approval'))
    conn.commit()
    order_id = c.lastrowid
    conn.close()
    return order_id

def get_orders():
    conn = sqlite3.connect("studio_orders.db")
    df = pd.read_sql_query("SELECT * FROM orders ORDER BY id DESC", conn)
    conn.close()
    return df

def update_status(order_id, new_status):
    conn = sqlite3.connect("studio_orders.db")
    c = conn.cursor()
    c.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
    conn.commit()
    conn.close()

def generate_upi_qr(upi_id, amount, note):
    upi_url = f"upi://pay?pa={upi_id}&pn=Studio&am={amount}&tn={urllib.parse.quote(note)}&cu=INR"
    qr = qrcode.make(upi_url)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    return buffer.getvalue()

# ================= পেজ লেআউট =================
st.set_page_config(page_title="Studio Order Portal", page_icon="📸", layout="wide")

menu = st.sidebar.radio("Navigation", ["অর্ডার করুন (Customer)", "অ্যাডমিন প্যানেল (Admin)"])

# ================= কাস্টমার ফর্ম =================
if menu == "অর্ডার করুন (Customer)":
    st.title("📸 অনলাইন ফটো প্রিন্ট ও প্রি-পেইড অর্ডার")
    st.write("আপনার ছবি ও পেমেন্টের বিবরণ জমা দিলে অর্ডার কনফার্ম হবে।")
    st.write("---")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("১. অর্ডারের বিবরণ")
        name = st.text_input("আপনার পুরো নাম *")
        phone = st.text_input("মোবাইল নম্বর (WhatsApp) *")
        service = st.selectbox("সার্ভিসের ধরন", list(SERVICE_PRICES.keys()))
        copies = st.number_input("কপি সংখ্যা", min_value=1, value=1, step=1)
        
        unit_price = SERVICE_PRICES[service]
        total_bill = unit_price * copies
        st.info(f"💰 প্রদেয় মোট বিল: **₹{total_bill}** ({copies} কপি × ₹{unit_price})")

        uploaded_photo = st.file_uploader("প্রিন্টের জন্য ফটো আপলোড করুন *", type=["jpg", "jpeg", "png"], key="photo")
        instruction = st.text_area("বিশেষ নির্দেশনা (যেমন: ব্যাকগ্রাউন্ড কালার, মাপ ইত্যাদি)")

    with col2:
        st.subheader("২. পেমেন্ট ভেরিফিকেশন (বাধ্যতামূলক)")
        st.write(f"👉 নিচের QR কোডটি স্ক্যান করে **₹{total_bill}** পেমেন্ট করুন:")
        
        qr_img = generate_upi_qr(STUDIO_UPI_ID, total_bill, f"Order {phone}")
        st.image(qr_img, width=210, caption=f"Scan & Pay ₹{total_bill}")

        txn_id = st.text_input("UPI Transaction ID / UTR নম্বর (১২ সংখ্যার) *")
        uploaded_receipt = st.file_uploader("পেমেন্টের স্ক্রিনশট আপলোড করুন *", type=["jpg", "jpeg", "png"], key="receipt")

    st.write("---")
    submit = st.button("পেমেন্ট সম্পন্ন হয়েছে - অর্ডার কনফার্ম করুন", use_container_width=True)

    if submit:
        if not name or not phone or not uploaded_photo:
            st.error("দয়া করে নাম, ফোন এবং মূল ছবি আপলোড করুন।")
        elif not txn_id or not uploaded_receipt:
            st.error("❌ পেমেন্ট সম্পন্ন না করে এবং UTR নম্বর ও রসিদ ছাড়া অর্ডার কনফার্ম হবে না!")
        else:
            timestamp = int(datetime.now().timestamp())
            
            # মূল ছবি সেভ
            ext_photo = os.path.splitext(uploaded_photo.name)[1]
            photo_path = os.path.join(UPLOAD_FOLDER, f"{phone}_{timestamp}_photo{ext_photo}")
            with open(photo_path, "wb") as f:
                f.write(uploaded_photo.getbuffer())

            # পেমেন্ট রসিদ সেভ
            ext_rcpt = os.path.splitext(uploaded_receipt.name)[1]
            receipt_path = os.path.join(PAYMENT_PROOFS, f"{phone}_{timestamp}_receipt{ext_rcpt}")
            with open(receipt_path, "wb") as f:
                f.write(uploaded_receipt.getbuffer())

            # ডাটাবেসে এন্ট্রি
            order_id = insert_order(name, phone, service, copies, total_bill, txn_id, receipt_path, instruction, photo_path)
            
            st.success(f"🎉 ধন্যবাদ {name}! আপনার পেমেন্ট রেকর্ড করা হয়েছে। অর্ডার আইডি: #{order_id}")
            
            # WhatsApp বাটন
            msg = f"নমস্কার, আমি স্টুডিওতে অনলাইন পেমেন্ট করে অর্ডার দিয়েছি।\nঅর্ডার আইডি: #{order_id}\nনাম: {name}\nবিল: ₹{total_bill}\nTxn ID: {txn_id}"
            wa_url = f"https://wa.me/{STUDIO_WHATSAPP}?text={urllib.parse.quote(msg)}"
            st.link_button("📲 স্টুডিওর WhatsApp-এ রসিদ পাঠিয়ে কনফার্ম করুন", wa_url, use_container_width=True)

# ================= অ্যাডমিন প্যানেল =================
elif menu == "অ্যাডমিন প্যানেল (Admin)":
    st.title("🛠 স্টুডিও কন্ট্রোল ও পেমেন্ট ভেরিফিকেশন")
    admin_pass = st.sidebar.text_input("পাসওয়ার্ড", type="password")

    if admin_pass == "admin123":
        orders_df = get_orders()
        if orders_df.empty:
            st.info("কোনো অর্ডার আসেনি।")
        else:
            st.write(f"### মোট অর্ডার: {len(orders_df)}")
            for _, row in orders_df.iterrows():
                with st.expander(f"অর্ডার #{row['id']} - {row['customer_name']} | ₹{row['total_price']} [{row['status']}]"):
                    col_info, col_img, col_pay = st.columns([1.5, 1, 1])
                    
                    with col_info:
                        st.write(f"**তারিখ:** {row['date']}")
                        st.write(f"**গ্রাহকের ফোন:** {row['phone']}")
                        st.write(f"**সার্ভিস:** {row['service_type']} ({row['copies']} কপি)")
                        st.write(f"**মোট বিল:** ₹{row['total_price']}")
                        st.write(f"**UPI UTR/Txn ID:** `{row['payment_txn_id']}`")
                        st.write(f"**নির্দেশ:** {row['instruction'] if row['instruction'] else 'নেই'}")
                        
                        current_status = row['status']
                        new_status = st.selectbox(
                            "অর্ডারের অগ্রগতি পরিবর্তন:",
                            ["Paid - Pending Approval", "Confirmed & Editing", "Printed", "Ready for Delivery", "Delivered"],
                            index=["Paid - Pending Approval", "Confirmed & Editing", "Printed", "Ready for Delivery", "Delivered"].index(current_status),
                            key=f"status_{row['id']}"
                        )
                        if new_status != current_status:
                            update_status(row['id'], new_status)
                            st.rerun()

                    with col_img:
                        st.write("**কাস্টমারের ফটো:**")
                        if os.path.exists(row['file_path']):
                            st.image(row['file_path'], width=150)
                            with open(row['file_path'], "rb") as f:
                                st.download_button("ফটো ডাউনলোড", data=f, file_name=os.path.basename(row['file_path']), key=f"dl_photo_{row['id']}")

                    with col_pay:
                        st.write("**পেমেন্টের স্ক্রিনশট:**")
                        if os.path.exists(row['payment_proof_path']):
                            st.image(row['payment_proof_path'], width=150)
                            with open(row['payment_proof_path'], "rb") as f:
                                st.download_button("স্ক্রিনশট ডাউনলোড", data=f, file_name=os.path.basename(row['payment_proof_path']), key=f"dl_rcpt_{row['id']}")

    elif admin_pass != "":
        st.error("ভুল পাসওয়ার্ড!")