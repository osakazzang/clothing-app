import streamlit as st
import requests
import base64
import cv2
import numpy as np
from PIL import Image
from pyzbar.pyzbar import decode

# 1. 設定：GASのウェブアプリURL
GAS_URL = "https://script.google.com/macros/s/AKfycbwNrmeONTiaba4hZSnmCwLAeuysJV_eeQqoHpJo2bDur8JI_sqSNpuzsEMLpxAbKgYOIw/exec"

st.title("衣類データ登録App")

# 複数バーコードを覚えておくためのリスト
if 'barcodes' not in st.session_state:
    st.session_state.barcodes = []

st.subheader("🔍 バーコード読み取り（強力版）")
st.write("サイズ違いなど、複数のバーコードを続けて撮影できます。薄暗くても読み取りやすくなりました！")
st.write("💡 コツ: ピントを合わせるために、バーコードから **15cm〜20cm** ほど離して撮影してください。")

barcode_pic = st.camera_input("📷 バーコードを撮影してください", key="barcode_camera")

if barcode_pic is not None:
    # 1. 撮影された画像をPillowで開く
    pil_image = Image.open(barcode_pic).convert('RGB')
    
    # 2. OpenCVで処理できるようにNumpy配列に変換
    cv_image = np.array(pil_image)
    
    # 3. カラー画像をグレースケール（白黒）に変換
    gray = cv2.cvtColor(cv_image, cv2.COLOR_RGB2GRAY)
    
    # ★魔法の処理：影や暗さを飛ばして、強制的に白と黒だけのバキバキの画像にする（適応的二値化）
    thresh = cv2.adaptiveThreshold(
        gray, 255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 
        11, 2
    )
    
    # 4. まずは「バキバキに補正した画像」でバーコードを探す
    decoded_objects = decode(thresh)
    
    # 5. もし補正画像で見つからなければ、保険として「元のカラー画像」でもう一度探す
    if not decoded_objects:
        decoded_objects = decode(cv_image)
    
    # 結果の判定
    if decoded_objects:
        for obj in decoded_objects:
            code = obj.data.decode("utf-8")
            if code not in st.session_state.barcodes:
                st.session_state.barcodes.append(code)
                st.success(f"✅ 追加しました: {code}")
            else:
                st.info(f"💡 既に登録済みの番号です: {code}")
    else:
        st.error("❌ バーコードが見つかりません。もう少し離すか、明るい場所で再度撮影してください。")

# リストに入っている複数のバーコードをカンマでつなぐ
joined_barcodes = ", ".join(st.session_state.barcodes)

# アイテム名の入力欄
item_name = st.text_input("アイテム名（手入力・修正も可）", value=joined_barcodes)

if st.button("🗑️ バーコードの読み取りをやり直す"):
    st.session_state.barcodes = []
    st.rerun()

st.divider()

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
                    st.success("🎉 DBへの保存が完了しました！")
                    st.session_state.barcodes = []
                else:
                    st.error(f"❌ 通信エラー（コード: {response.status_code}）")
            except Exception as e:
                st.error(f"❌ エラーが発生しました: {e}")
