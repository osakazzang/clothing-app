import streamlit as st
import requests
import base64
import cv2
import numpy as np
from PIL import Image
from pyzbar.pyzbar import decode
import time

# ==========================================
# 0. ページ設定とUIカスタマイズ（一番最初に書く必要があります）
# ==========================================
st.set_page_config(
    page_title="衣類データ登録",
    page_icon="👕",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- CSSによる強制的なデザイン変更（ネイティブアプリ風） ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;} /* 右上のメニューを隠す */
            footer {visibility: hidden;}    /* 下のロゴを隠す */
            header {visibility: hidden;}    /* 上の空白を消す */
            
            /* ボタンをスマホで押しやすく、スタイリッシュに */
            div.stButton > button:first-child {
                background-color: #007AFF;
                color: white;
                border-radius: 10px;
                height: 3em;
                font-weight: bold;
                border: none;
                width: 100%;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            div.stButton > button:first-child:hover {
                background-color: #0056b3;
            }
            
            /* セクション見出しのデザイン */
            h3 {
                color: #007AFF;
                border-bottom: 2px solid #007AFF;
                padding-bottom: 5px;
                margin-top: 30px;
                font-size: 1.2rem;
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# ==========================================
# 1. アプリのメインロジック
# ==========================================
GAS_URL = "https://script.google.com/macros/s/AKfycbwNrmeONTiaba4hZSnmCwLAeuysJV_eeQqoHpJo2bDur8JI_sqSNpuzsEMLpxAbKgYOIw/exec"

st.title("👕 衣類データ登録")

if 'barcodes' not in st.session_state:
    st.session_state.barcodes = []

# --- セクション1: バーコード ---
st.markdown("### 🔍 バーコード・アイテム名")
st.caption("バーコードから15〜20cm離して撮影するとピントが合いやすいです。")

barcode_pic = st.camera_input("📷 バーコードを撮影", key="barcode_camera")

if barcode_pic is not None:
    pil_image = Image.open(barcode_pic).convert('RGB')
    cv_image = np.array(pil_image)
    gray = cv2.cvtColor(cv_image, cv2.COLOR_RGB2GRAY)
    
    thresh = cv2.adaptiveThreshold(
        gray, 255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 
        11, 2
    )
    
    decoded_objects = decode(thresh)
    if not decoded_objects:
        decoded_objects = decode(cv_image)
    
    if decoded_objects:
        for obj in decoded_objects:
            code = obj.data.decode("utf-8")
            if code not in st.session_state.barcodes:
                st.session_state.barcodes.append(code)
                st.toast(f"✅ 追加: {code}") # スマホ風のトースト通知
            else:
                st.toast(f"💡 登録済み: {code}")
    else:
        st.error("❌ 読み取れませんでした。少し離して再撮影してください。")

joined_barcodes = ", ".join(st.session_state.barcodes)
item_name = st.text_input("アイテム名 (自動入力 / 編集可)", value=joined_barcodes)

# やり直しボタンを少し小さめに配置
col1, col2 = st.columns([2, 1])
with col2:
    if st.button("🗑️ リセット"):
        st.session_state.barcodes = []
        st.rerun()

# --- セクション2: 写真撮影 ---
st.markdown("### 📸 状態の撮影")
col_front, col_back = st.columns(2)
with col_front:
    front_pic = st.camera_input("👕 本体", key="front_camera")
with col_back:
    back_pic = st.camera_input("👕 パーツ", key="back_camera")

# --- セクション3: ラベル ---
st.markdown("### 🏷️ ケアラベル")
label_pics = st.file_uploader("写真ライブラリから複数選択", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])

def convert_image(uploaded_file):
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        base64_data = base64.b64encode(bytes_data).decode('utf-8')
        return {"mimeType": uploaded_file.type, "bytes": base64_data}
    return None

# --- 送信ボタン ---
st.write("") # スペース空け
if st.button("💾 データを保存して送信", type="primary"):
    if not item_name or not front_pic or not back_pic or not label_pics:
        st.error("⚠️ すべての項目（アイテム名、本体、パーツ、ラベル）を埋めてください。")
    else:
        with st.spinner("🚀 クラウドへ送信中..."):
            try:
                payload = {
                    "itemName": item_name,
                    "fileFront": convert_image(front_pic),
                    "fileBack": convert_image(back_pic),
                    "fileLabels": [convert_image(pic) for pic in label_pics]
                }
                response = requests.post(GAS_URL, json=payload)
                
                if response.status_code == 200:
                    st.success("🎉 DBへの保存が完了しました！次のアイテムを登録できます。")
                    st.toast("保存完了！", icon="🎊")
                    st.session_state.barcodes = []
                    time.sleep(2) # 2秒待ってから画面をリセット
                    st.rerun()
                else:
                    st.error(f"❌ 通信エラー（コード: {response.status_code}）")
            except Exception as e:
                st.error(f"❌ エラーが発生しました: {e}")
