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

name1 = st.secrets.NAME1
name2 = st.secrets.NAME2


# 入力フォーム
st.header("支出の記録")
col1, col2 = st.columns(2)

with col1:
    st.subheader(name1)
    person_1_date = st.date_input(f"日付（{name1}）")
    person_1_amount = st.number_input(f"金額（{name1}）", min_value=0, step=100)
    if st.button(f"追加（{name1}）"):
        new_row = {
            "Person": name1,
            "Date": str(person_1_date),
            "Amount": person_1_amount,
        }
        data = pd.concat([data, pd.DataFrame([new_row])], ignore_index=True)
        save_data(sheet, data)
        st.success(f"{name1} の支出が追加されました！")

with col2:
    st.subheader(name2)
    person_2_date = st.date_input(f"日付（{name2}）")
    person_2_amount = st.number_input(f"金額（{name2}）", min_value=0, step=100)
    if st.button(f"追加（{name2}）"):
        new_row = {
            "Person": name2,
            "Date": str(person_2_date),
            "Amount": person_2_amount,
        }
        data = pd.concat([data, pd.DataFrame([new_row])], ignore_index=True)
        save_data(sheet, data)
        st.success(f"{name2} の支出が追加されました！")

# 表の表示
st.header("支出一覧")
st.dataframe(data)

# 精算機能
st.header("精算")
if st.button("精算する"):
    # Personごとの合計金額を計算
    total_person_1 = data[data["Person"] == name1]["Amount"].sum()
    total_person_2 = data[data["Person"] == name2]["Amount"].sum()

    # 精算計算
    total_spent = total_person_1 + total_person_2
    equal_share = total_spent / 2
    difference = total_person_1 - total_person_2

    if difference > 0:
        payer = name2
        payee = name1
        amount_to_pay = abs(difference) / 2
    elif difference < 0:
        payer = name1
        payee = name2
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
