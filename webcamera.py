import streamlit as st
import requests
import base64
from PIL import Image
from pyzbar.pyzbar import decode

# 1. 設定：GASのウェブアプリURL
GAS_URL = "https://script.google.com/macros/s/AKfycbxL4-4MWX1mF4TGJVeASeorEODDPq16T85WuSc77T5oxw1qJluo6agbPyzRFnu1g_GBpA/exec"

st.title("衣類データ登録アプリ 📱")

# --- 新機能：サーバー側でのバーコード解析 ---
st.subheader("🔍 バーコード読み取り")
barcode_pic = st.camera_input("📷 バーコードを接写して撮影してください", key="barcode_camera")

item_name_value = "" # 初期値は空

if barcode_pic is not None:
    # 撮影された画像をPythonサーバー上で開く
    image = Image.open(barcode_pic)
    # pyzbarを使って強力に解析
    decoded_objects = decode(image)
    
    if decoded_objects:
        # 解析成功：バーコードの番号を取り出す
        item_name_value = decoded_objects[0].data.decode("utf-8")
        st.success(f"✅ 読み取り成功: {item_name_value}")
    else:
        st.error("❌ バーコードが見つかりません。ピントを合わせて再度撮影してください。")

# アイテム名の入力欄（解析が成功すれば、自動的に番号が入ります）
item_name = st.text_input("アイテム名（手入力も可）", value=item_name_value)

st.divider() # 区切り線

# --- これまで通りの写真撮影 ---
st.subheader("1. 状態の撮影")
front_pic = st.camera_input("📷 前面の写真を撮影", key="front_camera")
back_pic = st.camera_input("📷 背面の写真を撮影", key="back_camera")

st.subheader("2. ケアラベルの選択")
label_pics = st.file_uploader("📁 スマホの写真ライブラリから選択（複数可）", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])

def convert_image(uploaded_file):
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        base64_data = base64.b64encode(bytes_data).decode('utf-8')
        return {"mimeType": uploaded_file.type, "bytes": base64_data}
    return None

# --- 送信処理 ---
if st.button("💾 データを保存する"):
    if not item_name or not front_pic or not back_pic or not label_pics:
        st.error("⚠️ すべての項目を入力・撮影・選択してください！")
    else:
        with st.spinner("データを送信中... 少々お待ちください⏳"):
            try:
                payload = {
                    "itemName": item_name,
                    "fileFront": convert_image(front_pic),
                    "fileBack": convert_image(back_pic),
                    "fileLabels": [convert_image(pic) for pic in label_pics]
                }
                response = requests.post(GAS_URL, json=payload)
                if response.status_code == 200:
                    st.success("🎉 スプレッドシートへの保存が完了しました！")
                else:
                    st.error(f"❌ 通信エラー（コード: {response.status_code}）")
            except Exception as e:
                st.error(f"❌ エラーが発生しました: {e}")