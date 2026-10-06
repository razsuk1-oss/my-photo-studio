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
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# আপনার তথ্য এখানে বসান:
STUDIO_UPI_ID = "9775917899@ybl"      # আপনার GPay/PhonePe UPI ID
STUDIO_WHATSAPP = "919775917899"         # দেশের কোডসহ আপনার WhatsApp নম্বর (যেমন: 91...)

# প্রতি সার্ভিসের দাম (টাকায়)
SERVICE_PRICES = {
    "পাসপোর্ট সাইজ ফটো (3.2 x 4 cm)": 40,
    "স্ট্যাম্প সাইজ ফটো": 40,
    "4R প্রিন্ট (4 x 6 ইঞ্চি)": 40,
    "A4 সাইজ ফ্রেম প্রিন্ট": 250,
    "আইডি কার্ড প্রিন্ট": 75
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
            payment_status TEXT,
            instruction TEXT,
            file_path TEXT,
            status TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def insert_order(name, phone, service, copies, total_price, payment_status, instruction, file_path):
    conn = sqlite3.connect("studio_orders.db")
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''
        INSERT INTO orders (date, customer_name, phone, service_type, copies, total_price, payment_status, instruction, file_path, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (now, name, phone, service, copies, total_price, payment_status, instruction, file_path, 'Pending'))
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

# UPI QR কোড তৈরি করার ফাংশন
def generate_upi_qr(upi_id, amount, note):
    upi_url = f"upi://pay?pa={upi_id}&pn=Studio&am={amount}&tn={urllib.parse.quote(note)}&cu=INR"
    qr = qrcode.make(upi_url)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    return buffer.getvalue()

# ================= পেজ লেআউট =================
st.set_page_config(page_title="Studio Photo Portal", page_icon="📸", layout="wide")

menu = st.sidebar.radio("Navigation", ["কাস্টমার অর্ডার ফর্ম", "স্টুডিও অ্যাডমিন প্যানেল"])

# ================= কাস্টমার ফর্ম =================
if menu == "কাস্টমার অর্ডার ফর্ম":
    st.title("📸 অনলাইন ফটো প্রিন্ট ও স্টুডিও অর্ডার")
    st.write("আপনার ছবি আপলোড করুন এবং প্রয়োজনীয় তথ্য দিয়ে ঘরে বসেই অর্ডার করুন।")
    st.write("---")

    col1, col2 = st.columns([1, 1])

    with col1:
        name = st.text_input("আপনার নাম *")
        phone = st.text_input("মোবাইল নম্বর (WhatsApp) *")
        service = st.selectbox("সার্ভিসের ধরন", list(SERVICE_PRICES.keys()))
        copies = st.number_input("কপি সংখ্যা", min_value=1, value=1, step=1)
        
        unit_price = SERVICE_PRICES[service]
        total_bill = unit_price * copies
        st.info(f"💰 মোট বিল: **₹{total_bill}** ({copies} কপি × ₹{unit_price})")

        uploaded_file = st.file_uploader("আপনার ফটো আপলোড করুন (JPG/PNG) *", type=["jpg", "jpeg", "png"])
        instruction = st.text_area("কোনো বিশেষ নির্দেশ (যেমন: ব্যাকগ্রাউন্ড কালার পরিবর্তন)")

    with col2:
        st.subheader("💳 পেমেন্ট মাধ্যম")
        pay_method = st.radio("পেমেন্ট কীভাবে করবেন?", ["UPI (GPay/PhonePe/Paytm QR)", "দোকানে এসে ক্যাশ দেবেন (Cash on Delivery)"])
        
        if pay_method.startswith("UPI"):
            st.write("নিচের QR কোডটি স্ক্যান করে পেমেন্ট করুন:")
            qr_img = generate_upi_qr(STUDIO_UPI_ID, total_bill, f"Order by {phone}")
            st.image(qr_img, width=220, caption=f"Scan to Pay ₹{total_bill}")

    submit = st.button("অর্ডার কনফার্ম করুন", use_container_width=True)

    if submit:
        if not name or not phone or not uploaded_file:
            st.error("দয়া করে নাম, ফোন নম্বর এবং ফটো সিলেক্ট করুন।")
        else:
            file_extension = os.path.splitext(uploaded_file.name)[1]
            saved_filename = f"{phone}_{int(datetime.now().timestamp())}{file_extension}"
            save_path = os.path.join(UPLOAD_FOLDER, saved_filename)
            
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            payment_status = "Online Paid (Verify)" if pay_method.startswith("UPI") else "Cash on Delivery"
            order_id = insert_order(name, phone, service, copies, total_bill, payment_status, instruction, save_path)
            
            st.success(f"🎉 ধন্যবাদ {name}! আপনার অর্ডার সফলভাবে জমা হয়েছে। অর্ডার আইডি: #{order_id}")
            
            # WhatsApp বাটন
            msg = f"নমস্কার, আমি স্টুডিও ওয়েবসাইটে একটি অর্ডার দিয়েছি।\nঅর্ডার আইডি: #{order_id}\nনাম: {name}\nসার্ভিস: {service} ({copies} কপি)\nবিল: ₹{total_bill}"
            wa_url = f"https://wa.me/{STUDIO_WHATSAPP}?text={urllib.parse.quote(msg)}"
            
            st.link_button("📲 স্টুডিওকে WhatsApp-এ মেসেজ পাঠান", wa_url, use_container_width=True)

# ================= অ্যাডমিন প্যানেল =================
elif menu == "স্টুডিও অ্যাডমিন প্যানেল":
    st.title("🛠 স্টুডিও কন্ট্রোল প্যানেল")
    admin_pass = st.sidebar.text_input("পাসওয়ার্ড", type="password")

    if admin_pass == "admin123":
        orders_df = get_orders()
        if orders_df.empty:
            st.info("কোনো অর্ডার জমা পড়েনি।")
        else:
            st.write(f"### মোট অর্ডার: {len(orders_df)}")
            for _, row in orders_df.iterrows():
                with st.expander(f"অর্ডার #{row['id']} - {row['customer_name']} | ₹{row['total_price']} ({row['status']})"):
                    c1, c2 = st.columns([2, 1])
                    with c1:
                        st.write(f"**তারিখ:** {row['date']}")
                        st.write(f"**ফোন:** {row['phone']}")
                        st.write(f"**সার্ভিস:** {row['service_type']} ({row['copies']} কপি)")
                        st.write(f"**পেমেন্ট স্ট্যাটাস:** `{row['payment_status']}`")
                        st.write(f"**নির্দেশ:** {row['instruction'] if row['instruction'] else 'নেই'}")
                        
                        # স্ট্যাটাস আপডেট
                        current_status = row['status']
                        new_status = st.selectbox(
                            "কাজের স্ট্যাটাস পরিবর্তন করুন:",
                            ["Pending", "Editing", "Printed", "Ready for Delivery", "Delivered"],
                            index=["Pending", "Editing", "Printed", "Ready for Delivery", "Delivered"].index(current_status),
                            key=f"status_{row['id']}"
                        )
                        if new_status != current_status:
                            update_status(row['id'], new_status)
                            st.rerun()

                    with c2:
                        if os.path.exists(row['file_path']):
                            st.image(row['file_path'], caption="কাস্টমারের আসল ছবি", width=180)
                            with open(row['file_path'], "rb") as file:
                                st.download_button(
                                    label="ছবি ডাউনলোড করুন",
                                    data=file,
                                    file_name=os.path.basename(row['file_path']),
                                    mime="image/jpeg",
                                    key=f"dl_{row['id']}"
                                )
    elif admin_pass != "":
        st.error("ভুল পাসওয়ার্ড!")