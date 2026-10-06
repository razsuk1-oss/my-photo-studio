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

# আপনার নিজস্ব তথ্য এখানে বসান:
STUDIO_UPI_ID = "your-upi-id@okaxis"      # আপনার UPI ID (PhonePe/GPay)
STUDIO_WHATSAPP = "919876543210"         # WhatsApp নম্বর (যেমন: 91...)

# প্রতি সার্ভিসের দাম
SERVICE_PRICES = {
    "পাসপোর্ট সাইজ ফটো (3.2 x 4 cm)": 50,
    "স্ট্যাম্প সাইজ ফটো": 40,
    "4R প্রিন্ট (4 x 6 ইঞ্চি)": 30,
    "A4 সাইজ ফ্রেম প্রিন্ট": 250,
    "আইডি কার্ড প্রিন্ট": 60
}

# ================= ডাটাবেস ফাংশন =================
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

def search_orders_by_customer(query_str):
    conn = sqlite3.connect("studio_orders.db")
    query_clean = str(query_str).strip()
    
    # আইডি অথবা ফোন নম্বর দিয়ে খোঁজা
    query = """
        SELECT * FROM orders 
        WHERE phone LIKE ? OR id = ? 
        ORDER BY id DESC
    """
    df = pd.read_sql_query(query, conn, params=(f"%{query_clean}%", query_clean if query_clean.isdigit() else -1))
    conn.close()
    return df

def update_status(order_id, new_status):
    conn = sqlite3.connect("studio_orders.db")
    c = conn.cursor()
    c.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
    conn.commit()
    conn.close()

def generate_upi_qr(upi_id, amount, note):
    upi_url = f"upi://pay?pa={upi_id}&pn=STUDIO_RAZ&am={amount}&tn={urllib.parse.quote(note)}&cu=INR"
    qr = qrcode.make(upi_url)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    return buffer.getvalue()

# ================= পেজ লেআউট ও মেনু =================
st.set_page_config(page_title="STUDIO RAZ | Online Order Portal", page_icon="📸", layout="wide")

st.sidebar.markdown("<h2 style='text-align: center; color: #2563EB;'>📷 STUDIO RAZ</h2>", unsafe_allow_html=True)
menu = st.sidebar.radio("Navigation", ["কাস্টমার অর্ডার ফর্ম", "🔍 অর্ডার ট্র্যাক করুন", "স্টুডিও অ্যাডমিন প্যানেল"])

# ================= ১. কাস্টমার অর্ডার ফর্ম =================
if menu == "কাস্টমার অর্ডার ফর্ম":
    st.markdown("<h1 style='text-align: center; color: #1E3A8A; margin-bottom: 0;'>📸 STUDIO RAZ 📸</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray; font-size: 18px;'>অনলাইন ফটো প্রিন্টিং ও কাস্টমাইজেশন সার্ভিস</p>", unsafe_allow_html=True)
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
            qr_img = generate_upi_qr(STUDIO_UPI_ID, total_bill, f"STUDIO RAZ Order {phone}")
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
            
            st.success(f"🎉 ধন্যবাদ {name}! STUDIO RAZ-এ আপনার অর্ডার সফলভাবে জমা হয়েছে। অর্ডার আইডি: #{order_id}")
            st.warning("⚠️ আপনার এই **অর্ডার আইডি (#{order_id})** টি মনে রাখুন বা স্ক্রিনশট নিয়ে রাখুন, এটি দিয়ে পরে অর্ডারের কাজ কতদূর তা ট্র্যাক করতে পারবেন।")
            
            msg = f"নমস্কার STUDIO RAZ, আমি একটি অর্ডার দিয়েছি।\nঅর্ডার আইডি: #{order_id}\nনাম: {name}\nসার্ভিস: {service} ({copies} কপি)\nবিল: ₹{total_bill}"
            wa_url = f"https://wa.me/{STUDIO_WHATSAPP}?text={urllib.parse.quote(msg)}"
            st.link_button("📲 STUDIO RAZ-কে WhatsApp-এ মেসেজ পাঠান", wa_url, use_container_width=True)

# ================= ২. কাস্টমার অর্ডার ট্র্যাকিং =================
elif menu == "🔍 অর্ডার ট্র্যাক করুন":
    st.markdown("<h2 style='text-align: center; color: #1E3A8A;'>📦 আপনার অর্ডারের অগ্রগতি দেখুন</h2>", unsafe_allow_html=True)
    st.write("আপনার **অর্ডার আইডি** অথবা **মোবাইল নম্বর** দিয়ে সার্চ করুন:")
    
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        search_query = st.text_input("অর্ডার আইডি বা মোবাইল নম্বর লিখুন", placeholder="যেমন: 1 বা 9876543210")
    with col_t2:
        st.write("")
        st.write("")
        track_btn = st.button("সার্চ করুন", use_container_width=True)

    if track_btn and search_query:
        found_orders = search_orders_by_customer(search_query)
        if found_orders.empty:
            st.error("কোনো অর্ডার পাওয়া যায়নি। সঠিক অর্ডার আইডি বা মোবাইল নম্বর দিয়েছেন কি না যাচাই করুন।")
        else:
            st.success(f"{len(found_orders)} টি অর্ডার পাওয়া গেছে:")
            
            # স্ট্যাটাস কালার ও ব্যাজ
            status_colors = {
                "Pending": "🟠 অপেক্ষমাণ (Pending)",
                "Editing": "🔵 এডিটিং চলছে (Editing)",
                "Printed": "🟣 প্রিন্ট হয়ে গেছে (Printed)",
                "Ready for Delivery": "🟢 ডেলিভারির জন্য প্রস্তুত (Ready for Delivery)",
                "Delivered": "✅ ডেলিভারি সম্পন্ন (Delivered)"
            }

            for _, row in found_orders.iterrows():
                badge = status_colors.get(row['status'], row['status'])
                with st.container(border=True):
                    c_a, c_b = st.columns([2, 1])
                    with c_a:
                        st.subheader(f"অর্ডার #{row['id']} - {row['customer_name']}")
                        st.write(f"📅 **অর্ডারের তারিখ:** {row['date']}")
                        st.write(f"🖼 **সার্ভিস:** {row['service_type']} ({row['copies']} কপি)")
                        st.write(f"💵 **বিল:** ₹{row['total_price']} ({row['payment_status']})")
                    with c_b:
                        st.markdown("### বর্তমান স্ট্যাটাস:")
                        st.info(f"### {badge}")
                        if row['status'] == "Ready for Delivery":
                            st.success("🎉 আপনার ফটো সম্পূর্ণ রেডি! আপনি স্টুডিওতে এসে সংগ্রহ করতে পারেন।")

# ================= ৩. অ্যাডমিন প্যানেল =================
elif menu == "স্টুডিও অ্যাডমিন প্যানেল":
    st.markdown("<h2 style='color: #1E3A8A;'>🛠 STUDIO RAZ - কন্ট্রোল প্যানেল</h2>", unsafe_allow_html=True)
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
                        st.write(f"**পেমেন্ট:** `{row['payment_status']}`")
                        st.write(f"**নির্দেশ:** {row['instruction'] if row['instruction'] else 'নেই'}")
                        
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