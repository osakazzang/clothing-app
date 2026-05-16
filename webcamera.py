import streamlit as st
import requests
import base64
import cv2
import numpy as np
from PIL import Image
from pyzbar.pyzbar import decode
import time
import io

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
SECRET_TOKEN = st.secrets.get("SECRET_TOKEN", "my_secret_token_$0656$")

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

def compress_image(uploaded_file, max_size=(1000, 1000), quality=80):
    if uploaded_file is not None:
        try:
            img = Image.open(uploaded_file)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.thumbnail(max_size)
            
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=quality)
            
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
        # UI改善: プログレスバーとステータス表示用のプレースホルダーを作成
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # --- ステップ1: 画像圧縮 ---
            status_text.info("📦 画像を最適化しています... (1/2)")
            progress_bar.progress(25)
            
            payload = {
                "secret_token": SECRET_TOKEN,
                "itemName": item_name,
                "fileFront": compress_image(front_pic),
                "fileBack": compress_image(back_pic),
                "fileLabels": [compress_image(pic) for pic in label_pics]
            }
            
            # --- ステップ2: クラウド送信 ---
            progress_bar.progress(50)
            status_text.info("🚀 クラウドへデータを送信中... (2/2)")
            
            response = requests.post(GAS_URL, json=payload)
            progress_bar.progress(90)
            
            if response.status_code == 200:
                result_data = response.json()
                if result_data.get("status") == "error":
                    status_text.error(f"❌ サーバーエラー: {result_data.get('message')}")
                    progress_bar.empty()
                else:
                    # --- 完了処理 ---
                    progress_bar.progress(100)
                    status_text.success("🎉 DBへの保存が完了しました！")
                    st.balloons() # 視覚的な成功フィードバック（風船アニメーション）
                    st.toast("保存完了！", icon="🎊")
                    
                    # ユーザーに画面がリセットされることを案内
                    st.info("🔄 次のアイテムを登録するため、3秒後に画面をリセットします...")
                    time.sleep(3)
                    
                    # セッション状態をクリアして画面をリフレッシュ（リセット）
                    st.session_state.barcodes = []
                    st.rerun()
            else:
                status_text.error(f"❌ 通信エラー（コード: {response.status_code}）")
                progress_bar.empty()
        except Exception as e:
            status_text.error(f"❌ エラーが発生しました: {e}")
            progress_bar.empty()
