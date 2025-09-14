import datetime
import streamlit as st
import pandas as pd
import gspread
import plotly.graph_objects as go
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
    try:
        # 指定された名前のスプレッドシートを開く
        sheet = client.open(sheet_name).sheet1
        return sheet
    except gspread.SpreadsheetNotFound:
        # スプレッドシートが存在しない場合は新規作成
        sheet = client.create(sheet_name).sheet1
        # ヘッダーを設定
        headers = ["日付", "投資信託", "個別株", "米国株", "Folio",
                   "PayPay運用", "JREバンク", "合計", "増減"]
        sheet.append_row(headers)
        return sheet


# スプレッドシートからデータ読み込み
def load_data(sheet):
    try:
        records = sheet.get_all_records()
        if not records:
            columns = ["日付", "投資信託", "個別株", "米国株", "Folio",
                       "PayPay運用", "JREバンク", "合計", "増減"]
            return pd.DataFrame(columns=columns)
        return pd.DataFrame(records)
    except Exception:
        columns = ["日付", "投資信託", "個別株", "米国株", "Folio",
                   "PayPay運用", "JREバンク", "合計", "増減"]
        return pd.DataFrame(columns=columns)


# 前回の合計金額を取得
def get_previous_total(data):
    if data.empty:
        return None
    
    # 日付列をdatetimeに変換してソート
    data_copy = data.copy()
    data_copy["日付"] = pd.to_datetime(data_copy["日付"])
    data_sorted = data_copy.sort_values("日付", ascending=False)
    
    if len(data_sorted) > 0:
        latest_row = data_sorted.iloc[0]
        return int(latest_row.get("合計", 0))
    else:
        return None


# 増減率を計算
def calculate_change_rate(current_total, previous_total):
    if previous_total is None or previous_total == 0:
        return "初回"
    
    change_rate = ((current_total - previous_total) / previous_total) * 100
    if change_rate > 0:
        return f"+{change_rate:.1f}%"
    elif change_rate < 0:
        return f"{change_rate:.1f}%"
    else:
        return "0.0%"


# 期間でデータをフィルタリング
def filter_data_by_period(data, period):
    if data.empty:
        return data
    
    data_copy = data.copy()
    data_copy["日付"] = pd.to_datetime(data_copy["日付"])
    
    today = datetime.date.today()
    
    if period == "1ヶ月":
        start_date = today - datetime.timedelta(days=30)
    elif period == "半年":
        start_date = today - datetime.timedelta(days=180)
    elif period == "1年":
        start_date = today - datetime.timedelta(days=365)
    else:  # 全期間
        return data_copy
    
    filtered_data = data_copy[data_copy["日付"] >= pd.Timestamp(start_date)]
    return filtered_data


# 前日のデータを取得
def get_previous_day_data(data):
    if data.empty:
        return {"投資信託": 0, "個別株": 0, "米国株": 0, "Folio": 0,
                "PayPay運用": 0, "JREバンク": 0}
    
    # 日付列をdatetimeに変換してソート
    data_copy = data.copy()
    data_copy["日付"] = pd.to_datetime(data_copy["日付"])
    data_sorted = data_copy.sort_values("日付", ascending=False)
    
    if len(data_sorted) > 0:
        latest_row = data_sorted.iloc[0]
        return {
            "投資信託": int(latest_row.get("投資信託", 0)),
            "個別株": int(latest_row.get("個別株", 0)),
            "米国株": int(latest_row.get("米国株", 0)),
            "Folio": int(latest_row.get("Folio", 0)),
            "PayPay運用": int(latest_row.get("PayPay運用", 0)),
            "JREバンク": int(latest_row.get("JREバンク", 0))
        }
    else:
        return {"投資信託": 0, "個別株": 0, "米国株": 0, "Folio": 0,
                "PayPay運用": 0, "JREバンク": 0}


# 新しいデータを追加
def add_new_data(sheet, new_data):
    # データを行として追加（数値をPythonの標準型に変換）
    row_data = [
        new_data["日付"],
        int(new_data["投資信託"]) if new_data["投資信託"] != 0 else 0,
        int(new_data["個別株"]) if new_data["個別株"] != 0 else 0,
        int(new_data["米国株"]) if new_data["米国株"] != 0 else 0,
        int(new_data["Folio"]) if new_data["Folio"] != 0 else 0,
        int(new_data["PayPay運用"]) if new_data["PayPay運用"] != 0 else 0,
        int(new_data["JREバンク"]) if new_data["JREバンク"] != 0 else 0,
        int(new_data["合計"]) if new_data["合計"] != 0 else 0,
        new_data["増減"]
    ]
    sheet.append_row(row_data)


# アプリのタイトル
st.title("総資産集計アプリ")

# スプレッドシート名
SHEET_NAME = "assets"

# スプレッドシートへの接続
sheet = get_google_sheet(SHEET_NAME)

# データ読み込み
data = load_data(sheet)

# 前日のデータを取得
previous_data = get_previous_day_data(data)

# 前回の合計金額を取得
previous_total = get_previous_total(data)

# 今日の日付
today = datetime.date.today()

st.header("資産金額入力")
st.write(f"入力日: {today}")

# 入力フォーム
col1, col2 = st.columns(2)

with col1:
    st.subheader("投資商品")
    investment_trust = st.number_input(
        "投資信託",
        min_value=0,
        step=100,
        value=0,
        help=f"前回の金額: ¥{previous_data['投資信託']:,}"
    )
    individual_stocks = st.number_input(
        "個別株",
        min_value=0,
        step=100,
        value=0,
        help=f"前回の金額: ¥{previous_data['個別株']:,}"
    )
    us_stocks = st.number_input(
        "米国株",
        min_value=0,
        step=100,
        value=0,
        help=f"前回の金額: ¥{previous_data['米国株']:,}"
    )

with col2:
    st.subheader("その他の資産")
    folio = st.number_input(
        "Folio",
        min_value=0,
        step=100,
        value=0,
        help=f"前回の金額: ¥{previous_data['Folio']:,}"
    )
    paypay_investment = st.number_input(
        "PayPay運用",
        min_value=0,
        step=100,
        value=0,
        help=f"前回の金額: ¥{previous_data['PayPay運用']:,}"
    )
    jre_bank = st.number_input(
        "JREバンク",
        min_value=0,
        step=100,
        value=0,
        help=f"前回の金額: ¥{previous_data['JREバンク']:,}"
    )

# 決定ボタン
if st.button("決定", type="primary", use_container_width=True):
    # 入力されていない項目は前日の値を使用
    inv_trust = int(investment_trust if investment_trust > 0
                    else previous_data["投資信託"])
    ind_stocks = int(individual_stocks if individual_stocks > 0
                     else previous_data["個別株"])
    us_st = int(us_stocks if us_stocks > 0 else previous_data["米国株"])
    fol = int(folio if folio > 0 else previous_data["Folio"])
    paypay = int(paypay_investment if paypay_investment > 0
                 else previous_data["PayPay運用"])
    jre = int(jre_bank if jre_bank > 0 else previous_data["JREバンク"])

    final_data = {
        "日付": str(today),
        "投資信託": inv_trust,
        "個別株": ind_stocks,
        "米国株": us_st,
        "Folio": fol,
        "PayPay運用": paypay,
        "JREバンク": jre
    }

    # 合計を計算
    final_data["合計"] = int(
        final_data["投資信託"] +
        final_data["個別株"] +
        final_data["米国株"] +
        final_data["Folio"] +
        final_data["PayPay運用"] +
        final_data["JREバンク"]
    )
    
    # 増減率を計算
    final_data["増減"] = calculate_change_rate(
        final_data["合計"], previous_total
    )
    
    # スプレッドシートに追加
    try:
        add_new_data(sheet, final_data)
        st.success("データが正常に保存されました！")
        
        # データを再読み込み
        data = load_data(sheet)
        
    except Exception as e:
        st.error(f"データの保存に失敗しました: {str(e)}")

# 現在の表の値をすべて表示
st.header("資産履歴")

if not data.empty:
    # データを日付順（新しい順）でソート
    data_display = data.copy()
    data_display["日付"] = pd.to_datetime(data_display["日付"])
    data_display = data_display.sort_values("日付", ascending=False)

    # 数値列をフォーマット（増減列は文字列なので除外）
    numeric_columns = ["投資信託", "個別株", "米国株", "Folio", "PayPay運用",
                       "JREバンク", "合計"]
    for col in numeric_columns:
        if col in data_display.columns:
            data_display[col] = data_display[col].apply(
                lambda x: f"¥{x:,}" if pd.notnull(x) else "¥0"
            )

    # 日付を文字列形式に戻す
    data_display["日付"] = data_display["日付"].dt.strftime("%Y-%m-%d")

    st.dataframe(data_display, use_container_width=True)

    # グラフ表示
    st.header("資産推移グラフ")

    # 期間選択
    period_options = ["1ヶ月", "半年", "1年", "全期間"]
    selected_period = st.selectbox("表示期間を選択", period_options, index=3)

    # データをフィルタリング
    filtered_data = filter_data_by_period(data, selected_period)

    if not filtered_data.empty:
        # 日付順にソート
        chart_data = filtered_data.sort_values("日付")

        # 積み上げ棒グラフ用のデータ準備
        asset_columns = ["投資信託", "個別株", "米国株", "Folio", "PayPay運用",
                         "JREバンク"]

        # 日付を文字列に変換
        chart_data["日付_str"] = chart_data["日付"].dt.strftime("%Y-%m-%d")

        # 積み上げ棒グラフのコード（参考用にコメントアウト）
        # fig = go.Figure()
        #
        # colors = {
        #     "投資信託": "#FF6B6B",
        #     "個別株": "#4ECDC4",
        #     "米国株": "#45B7D1",
        #     "Folio": "#96CEB4",
        #     "JREバンク": "#FECA57"
        # }
        #
        # for column in asset_columns:
        #     if column in chart_data.columns:
        #         fig.add_trace(go.Bar(
        #             name=column,
        #             x=chart_data["日付_str"],
        #             y=chart_data[column],
        #             marker_color=colors.get(column, "#95A5A6")
        #         ))
        #
        # fig.update_layout(
        #     barmode='stack',
        #     title=f"資産推移 ({selected_period})",
        #     xaxis_title="日付",
        #     yaxis_title="金額 (円)",
        #     yaxis=dict(tickformat=","),
        #     legend=dict(
        #         orientation="h",
        #         yanchor="bottom",
        #         y=1.02,
        #         xanchor="right",
        #         x=1
        #     ),
        #     height=500
        # )
        #
        # st.plotly_chart(fig, use_container_width=True)

        # カラーパレット定義
        colors = {
            "投資信託": "#202A84",
            "個別株": "#4ECDC4",
            "米国株": "#9327D1",
            "Folio": "#FD7171",
            "PayPay運用": "#FA0000",
            "JREバンク": "#09B615",
        }

        # エリアグラフ（面積折れ線グラフ）
        st.subheader("資産推移グラフ")

        # エリアグラフの作成
        fig_area = go.Figure()

        # 各カテゴリのエリアを追加（積み上げ形式）
        for column in asset_columns:
            if column in chart_data.columns:
                fig_area.add_trace(go.Scatter(
                    name=column,
                    x=chart_data["日付_str"],
                    y=chart_data[column],
                    mode='lines',
                    stackgroup='one',  # 積み上げエリアグラフにする
                    line=dict(width=2, color=colors.get(column, "#95A5A6")),
                    fillcolor=colors.get(column, "#95A5A6"),
                    hovertemplate=f'<b>{column}</b><br>' +
                                  '日付: %{x}<br>' +
                                  '金額: ¥%{y:,}<extra></extra>'
                ))

        fig_area.update_layout(
            title=f"カテゴリ別資産推移 ({selected_period})",
            xaxis_title="日付",
            yaxis_title="金額 (円)",
            yaxis=dict(tickformat=","),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            height=500,
            hovermode='x unified'
        )

        st.plotly_chart(fig_area, use_container_width=True)
    else:
        st.info(f"選択した期間（{selected_period}）にデータがありません。")
else:
    st.info("まだデータがありません。上記のフォームから入力してください。")
