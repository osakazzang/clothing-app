import streamlit as st
import requests
import base64
import cv2
import numpy as np
from PIL import Image
from pyzbar.pyzbar import decode
import time
import io # 画像圧縮用に追加 (이미지 압축용으로 추가)

# ==========================================
# 0. ページ設定とUIカスタマイズ
# ==========================================
st.set_page_config(
    page_title="衣類データ登録",
    page_icon="👕",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- CSSによる強制的なデザイン変更 ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;} 
            footer {visibility: hidden;}    
            header {visibility: hidden;}    
            
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
GAS_URL = st.secrets["GAS_URL"]
# ★ 追加: セキュリティトークン（secrets.tomlで設定します）
SECRET_TOKEN = st.secrets.get("SECRET_TOKEN", "my_secret_token_$0907$")

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
                st.toast(f"✅ 追加: {code}") 
            else:
                st.toast(f"💡 登録済み: {code}")
    else:
        st.error("❌ 読み取れませんでした。少し離して再撮影してください。")

joined_barcodes = ", ".join(st.session_state.barcodes)
item_name = st.text_input("アイテム名 (自動入力 / 編集可)", value=joined_barcodes)

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

# ★ 変更: 画像を自動的に縮小・圧縮する関数
def compress_image(uploaded_file, max_size=(1000, 1000), quality=80):
    if uploaded_file is not None:
        try:
            # 画像を開く
            img = Image.open(uploaded_file)
            # JPEG保存のためにRGBモードに変換
            if img.mode != 'RGB':
                img = img.convert('RGB')
            # アスペクト比を維持してリサイズ（最大1000px）
            img.thumbnail(max_size)
            
            # メモリ上でJPEGとして圧縮保存
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=quality)
            
            # Base64エンコード
            base64_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return {"mimeType": "image/jpeg", "bytes": base64_data}
        except Exception as e:
            st.error(f"⚠️ 画像処理エラー: {e}")
            return None
    return None

# --- 送信ボタン ---
st.write("")
if st.button("💾 データを保存して送信", type="primary"):
    if not item_name or not front_pic or not back_pic or not label_pics:
        st.error("⚠️ すべての項目（アイテム名、本体、パーツ、ラベル）を埋めてください。")
    else:
        with st.spinner("🚀 データを圧縮してクラウドへ送信中..."):
            try:
                payload = {
                    "secret_token": SECRET_TOKEN, # ★ 追加: トークンを送信
                    "itemName": item_name,
                    "fileFront": compress_image(front_pic), # ★ 変更: 圧縮関数を使用
                    "fileBack": compress_image(back_pic),
                    "fileLabels": [compress_image(pic) for pic in label_pics]
                }
                response = requests.post(GAS_URL, json=payload)
                
                if response.status_code == 200:
                    result_data = response.json()
                    # GAS側でトークンエラー弾かれた場合の処理
                    if result_data.get("status") == "error":
                        st.error(f"❌ サーバーエラー: {result_data.get('message')}")
                    else:
                        st.success("🎉 DBへの保存が完了しました！次のアイテムを登録できます。")
                        st.toast("保存完了！", icon="🎊")
                        st.session_state.barcodes = []
                        time.sleep(2)
                        st.rerun()
                else:
                    st.error(f"❌ 通信エラー（コード: {response.status_code}）")
            except Exception as e:
                st.error(f"❌ エラーが発生しました: {e}")
