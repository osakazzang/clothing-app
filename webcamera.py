import streamlit as st
import requests
import base64
from PIL import Image
from pyzbar.pyzbar import decode

# 1. 設定：GASのウェブアプリURL
GAS_URL = "https://script.google.com/macros/s/AKfycbxL4-4MWX1mF4TGJVeASeorEODDPq16T85WuSc77T5oxw1qJluo6agbPyzRFnu1g_GBpA/exec"

st.title("衣類データ登録アプリ")

# --- 新機能：アプリに「記憶（メモリ）」を持たせる ---
# 複数バーコードを覚えておくためのリストを準備します
if 'barcodes' not in st.session_state:
    st.session_state.barcodes = []

st.subheader("🔍 バーコード読み取り（複数対応）")
st.write("サイズ違いなど、複数のバーコードを続けて撮影できます。")

barcode_pic = st.camera_input("📷 バーコードを接写して撮影してください", key="barcode_camera")

if barcode_pic is not None:
    # 撮影された画像をPythonサーバー上で開く
    image = Image.open(barcode_pic)
    # pyzbarを使って強力に解析
    decoded_objects = decode(image)
    
    if decoded_objects:
        # 読み取ったすべてのバーコードをチェック
        for obj in decoded_objects:
            code = obj.data.decode("utf-8")
            # まだリストにない新しい番号なら追加する
            if code not in st.session_state.barcodes:
                st.session_state.barcodes.append(code)
                st.success(f"✅ 追加しました: {code}")
            else:
                st.info(f"💡 既に登録済みの番号です: {code}")
    else:
        st.error("❌ バーコードが見つかりません。ピントを合わせて再度撮影してください。")

# リストに入っている複数のバーコードを「カンマ(,)」でつないで一つの文字列にする
joined_barcodes = ", ".join(st.session_state.barcodes)

# アイテム名の入力欄（複数のバーコードが自動で入ります）
item_name = st.text_input("アイテム名（手入力・修正も可）", value=joined_barcodes)

# 間違えて読み取ってしまった時のためのリセットボタン
if st.button("🗑️ バーコードの読み取りをやり直す"):
    st.session_state.barcodes = []
    st.rerun() # 画面を更新してリセットを反映する

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
                    # ★重要：保存に成功したら、次回の入力のためにバーコードの記憶を消去する
                    st.session_state.barcodes = []
                else:
                    st.error(f"❌ 通信エラー（コード: {response.status_code}）")
            except Exception as e:
                st.error(f"❌ エラーが発生しました: {e}")