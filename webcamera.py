import streamlit as st
import requests
import base64

# 1. 設定：先ほどGASでコピーした「ウェブアプリのURL」をここに貼り付けます
GAS_URL = "https://script.google.com/macros/s/AKfycbxL4-4MWX1mF4TGJVeASeorEODDPq16T85WuSc77T5oxw1qJluo6agbPyzRFnu1g_GBpA/exec"

# 画面のタイトルと説明
st.title("衣類データ登録アプリ 📱")
st.write("スマートフォンのカメラで撮影して、データを保存します。")

# 2. アイテム名の入力欄
item_name = st.text_input("アイテム名（手入力するか、スキャナーで読み取る）")

# 3. カメラ撮影エリア（前面・背面）
st.subheader("1. 前面と背面の撮影")
front_pic = st.camera_input("📷 前面の写真を撮影")
back_pic = st.camera_input("📷 背面の写真を撮影")

# 4. ケアラベル選択エリア（複数）
st.subheader("2. ケアラベルの選択")
st.info("※ケアラベルはスマホの標準カメラで先に撮影しておき、ここから複数選択してください。")
label_pics = st.file_uploader("📁 ケアラベルの写真を選択（複数可）", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])

# （裏側の処理）画像をGASへ送れる形式（Base64）に変換する関数
def convert_image(uploaded_file):
    if uploaded_file is not None:
        # 画像のデータを取り出して文字に変換
        bytes_data = uploaded_file.getvalue()
        base64_data = base64.b64encode(bytes_data).decode('utf-8')
        return {"mimeType": uploaded_file.type, "bytes": base64_data}
    return None

# 5. 送信ボタンと保存処理
if st.button("💾 データを保存する"):
    # 入力漏れがないかチェック
    if not item_name or not front_pic or not back_pic or not label_pics:
        st.error("⚠️ すべての項目を入力・撮影・選択してください！")
    else:
        # 送信中のクルクル回るアニメーションを表示
        with st.spinner("データを送信中... 少々お待ちください⏳"):
            try:
                # GASへ送るデータの小包（ペイロード）を作る
                payload = {
                    "itemName": item_name,
                    "fileFront": convert_image(front_pic),
                    "fileBack": convert_image(back_pic),
                    "fileLabels": [convert_image(pic) for pic in label_pics]
                }

                # GASの受付窓口へデータを投げる（POST通信）
                response = requests.post(GAS_URL, json=payload)
                
                # 結果の確認
                if response.status_code == 200:
                    st.success("🎉 スプレッドシートへの保存が完了しました！")
                else:
                    st.error(f"❌ 通信エラーが発生しました（コード: {response.status_code}）")
            except Exception as e:
                st.error(f"❌ エラーが発生しました: {e}")