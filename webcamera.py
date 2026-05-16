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
            
            /* スマホの画面上部の無駄な余白を極限まで削る */
            .block-container {
                padding-top: 1.5rem !important;
                padding-bottom: 1rem !important;
            }
            
            /* 💾 送信ボタン (Primary) のデザイン: 青色 */
            div.stButton > button[kind="primary"] {
                background-color: #007AFF !important;
                color: white !important;
                border-radius: 10px !important;
                height: 3.5em !important;
                font-weight: bold !important;
                width: 100% !important;
                border: none !important;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            
            /* メインタイトルを小さくスッキリと、文字色を白色に変更 */
            .main-title {
                text-align: center;
                font-size: 1.5rem;
                font-weight: bold;
                color: white; 
                margin-bottom: 5px;
            }
            
            /* セクション見出し(h3)のデザイン: サイズを従来の50% (0.8rem程度) に変更 */
            h3 {
                color: #007AFF !important;
                border-bottom: 2px solid #007AFF !important;
                padding-bottom: 5px !important;
                margin-top: 15px !important;
                font-size: 0.8rem !important; 
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# ==========================================
# 1. アプリのメインロジック
# ==========================================
GAS_URL = st.secrets["GAS_URL"]
SECRET_TOKEN = st.secrets["SECRET_TOKEN"]

st.markdown("<div class='main-title'>👕 衣類データ登録</div>", unsafe_allow_html=True)

if 'barcodes' not in st.session_state:
    st.session_state.barcodes = []
if 'form_key' not in st.session_state:
    st.session_state.form_key = 0
if 'barcode_key' not in st.session_state:
    st.session_state.barcode_key = 0

current_key = st.session_state.form_key
current_barcode_key = st.session_state.barcode_key
text_input_key = f"item_name_{current_key}"

# --- セクション1: バーコード ---
st.markdown("### 🔍 バーコード・アイテム名")
st.caption("ボタンを押してカメラを起動し、バーコードを撮影してください。")

barcode_pic = st.file_uploader("📷 バーコード画像", type=['png', 'jpg', 'jpeg'], key=f"barcode_upload_{current_barcode_key}")

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
                
                current_text = st.session_state.get(text_input_key, "")
                if current_text and code not in current_text:
                    st.session_state[text_input_key] = current_text + ", " + code
                elif not current_text:
                    st.session_state[text_input_key] = code
            else:
                st.toast(f"💡 登録済み: {code}")
        
        time.sleep(1.5)
        st.session_state.barcode_key += 1
        st.rerun()
    else:
        st.error("❌ 読み取れませんでした。別の写真で再撮影してください。")
        time.sleep(2.0)
        st.session_state.barcode_key += 1
        st.rerun()

joined_barcodes = ", ".join(st.session_state.barcodes)
item_name = st.text_input("アイテム名 (自動入力 / 編集可)", value=joined_barcodes, key=text_input_key)

# --- セクション2: 写真撮影 ---
st.markdown("### 📸 状態の撮影")
col_front, col_back = st.columns(2)
with col_front:
    front_pic = st.file_uploader("👕 本体", type=['png', 'jpg', 'jpeg'], key=f"front_upload_{current_key}")
with col_back:
    back_pic = st.file_uploader("👕 パーツ", type=['png', 'jpg', 'jpeg'], key=f"back_upload_{current_key}")

# --- セクション3: ラベル ---
st.markdown("### 🏷️ ケアラベル")
label_pics = st.file_uploader("複数選択可（カメラ / ライブラリ）", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'], key=f"label_pics_{current_key}")

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

# ==========================================
# ★ アプリ下部: 送信ボタン エリア (安定したエラー処理を追加)
# ==========================================
st.markdown("<br>", unsafe_allow_html=True) 

if st.button("💾 保存して送信", type="primary"):
    if not item_name or not front_pic or not back_pic or not label_pics:
        st.error("⚠️ すべての項目（アイテム名、本体、パーツ、ラベル）を埋めてください。")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.info("📦 画像を最適化しています... (1/2)")
            progress_bar.progress(25)
            
            payload = {
                "secret_token": SECRET_TOKEN,
                "itemName": item_name,
                "fileFront": compress_image(front_pic),
                "fileBack": compress_image(back_pic),
                "fileLabels": [compress_image(pic) for pic in label_pics]
            }
            
            progress_bar.progress(50)
            status_text.info("🚀 クラウドへデータを送信中... 最大15秒かかります (2/2)")
            
            # ★ 変更点: timeout(15秒)を設定し、サーバーからの応答を待つ上限を決定
            response = requests.post(GAS_URL, json=payload, timeout=15)
            progress_bar.progress(90)
            
            if response.status_code == 200:
                result_data = response.json()
                if result_data.get("status") == "error":
                    status_text.error(f"❌ サーバーエラー: {result_data.get('message')}")
                    progress_bar.empty()
                else:
                    progress_bar.progress(100)
                    status_text.success("🎉 DBへの保存が完了しました！")
                    st.balloons()
                    st.toast("保存完了！", icon="🎊")
                    
                    st.info("🔄 次のアイテムを登録するため、3秒後に画面をリセットします...")
                    time.sleep(3)
                    
                    st.session_state.barcodes = []
                    st.session_state.form_key += 1
                    st.session_state.barcode_key += 1
                    st.rerun()
            else:
                status_text.error(f"❌ 通信エラー（コード: {response.status_code}）: サーバーに問題が発生しました。")
                progress_bar.empty()
                
        # ★ 変更点: 細分化されたエラー処理 (例外処理) を追加
        except requests.exceptions.Timeout:
            status_text.error("❌ タイムアウトエラー: サーバーからの応答がありません。ネットワーク環境を確認して再試行してください。")
            progress_bar.empty()
        except requests.exceptions.ConnectionError:
            status_text.error("❌ ネットワークエラー: インターネットに接続されていません。接続を確認してください。")
            progress_bar.empty()
        except requests.exceptions.RequestException as e:
            status_text.error(f"❌ 通信エラーが発生しました: {e}")
            progress_bar.empty()
        except Exception as e:
            status_text.error(f"❌ 予期せぬエラーが発生しました: {e}")
            progress_bar.empty()
