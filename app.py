import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials


# Google Sheets API認証
def authenticate_google_sheets():
    google_credentials = st.secrets["GOOGLE_CREDENTIALS"]
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(
        google_credentials, scope
    )
    client = gspread.authorize(credentials)
    return client


# スプレッドシートへの接続
def get_google_sheet(sheet_name):
    client = authenticate_google_sheets()
    sheet = client.open(sheet_name).sheet1  # 最初のシートを取得
    return sheet


# スプレッドシートからデータ読み込み
def load_data(sheet):
    records = sheet.get_all_records()  # シート全体を取得
    return pd.DataFrame(records)


# データフレームをスプレッドシートに保存
def save_data(sheet, data):
    sheet.clear()  # シート内容をクリア
    sheet.update(
        [data.columns.values.tolist()] + data.values.tolist()
    )  # ヘッダーとデータを書き込み


# アプリのタイトル
st.title("家計管理アプリ")

# スプレッドシート名
SHEET_NAME = "kakei_seisan"

# スプレッドシートへの接続
sheet = get_google_sheet(SHEET_NAME)

# データ読み込み
try:
    data = load_data(sheet)
except Exception:
    data = pd.DataFrame(columns=["Person", "Date", "Amount"])


# 入力フォーム
st.header("支出の記録")
col1, col2 = st.columns(2)

with col1:
    st.subheader("たく")
    person_1_date = st.date_input("日付（たく）")
    person_1_amount = st.number_input("金額（たく）", min_value=0, step=100)
    if st.button("追加（たく）"):
        new_row = {
            "Person": "たく",
            "Date": str(person_1_date),
            "Amount": person_1_amount,
        }
        data = pd.concat([data, pd.DataFrame([new_row])], ignore_index=True)
        save_data(sheet, data)
        st.success("たく の支出が追加されました！")

with col2:
    st.subheader("めい")
    person_2_date = st.date_input("日付（めい）")
    person_2_amount = st.number_input("金額（めい）", min_value=0, step=100)
    if st.button("追加（めい）"):
        new_row = {
            "Person": "めい",
            "Date": str(person_2_date),
            "Amount": person_2_amount,
        }
        data = pd.concat([data, pd.DataFrame([new_row])], ignore_index=True)
        save_data(sheet, data)
        st.success("めい の支出が追加されました！")

# 表の表示
st.header("支出一覧")
st.dataframe(data)

# 精算機能
st.header("精算")
if st.button("精算する"):
    # Personごとの合計金額を計算
    total_person_1 = data[data["Person"] == "たく"]["Amount"].sum()
    total_person_2 = data[data["Person"] == "めい"]["Amount"].sum()

    # 精算計算
    total_spent = total_person_1 + total_person_2
    equal_share = total_spent / 2
    difference = total_person_1 - total_person_2

    if difference > 0:
        payer = "めい"
        payee = "たく"
        amount_to_pay = abs(difference) / 2
    elif difference < 0:
        payer = "たく"
        payee = "めい"
        amount_to_pay = abs(difference) / 2
    else:
        payer, payee, amount_to_pay = None, None, None

    # 結果表示
    if payer and payee:
        st.write(f"{payer} が {payee} に ¥{amount_to_pay:.0f} 支払う必要があります。")
    else:
        st.write("精算する必要はありません。")

    # データクリア
    data = pd.DataFrame(columns=["Person", "Date", "Amount"])
    save_data(sheet, data)
    st.success("精算が完了しました！表の内容はクリアされました。")
