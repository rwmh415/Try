import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- 核心邏輯：自定義 ADX 計算函數 (修正維度問題) ---
def calculate_adx(df, length=14):
    # 強制將資料轉為一維 Series，避免 MultiIndex 報錯
    high = df['High'].squeeze()
    low = df['Low'].squeeze()
    close = df['Close'].squeeze()
    
    # 計算 TR (True Range)
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # 計算方向變動 (DM)
    up_move = high.diff()
    down_move = low.diff()
    
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), abs(down_move), 0)
    
    # 使用簡單移動平均
    atr = tr.rolling(window=length).mean()
    plus_di = 100 * (pd.Series(plus_dm, index=df.index).rolling(window=length).mean() / atr)
    minus_di = 100 * (pd.Series(minus_dm, index=df.index).rolling(window=length).mean() / atr)
    
    dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di))
    adx = dx.rolling(window=length).mean()
    return adx

# --- 網頁配置 ---
st.set_page_config(page_title="日內交易決策系統", layout="wide")
st.title("📊 日內交易決策系統 (穩定修復版)")

# --- 側邊欄設定 ---
st.sidebar.header("設定參數")
ticker = st.sidebar.text_input("輸入股票/期貨代碼 (如: NQ=F, TSLA)", "NQ=F")
va_threshold = st.sidebar.number_input("VA 寬度分水嶺 (%)", value=0.35, step=0.01)
adx_threshold = st.sidebar.number_input("ADX 強弱分水嶺", value=25.0, step=1.0)

if st.sidebar.button("開始分析"):
    with st.spinner(f"正在抓取 {ticker} 實時數據..."):
        try:
            # 使用 auto_adjust=True 簡化資料結構
            df = yf.download(ticker, period="5d", interval="15m", auto_adjust=True)
            
            if df.empty:
                st.error("找不到數據，請確認代碼是否正確。")
            else:
                # 執行計算
                df['ADX_14'] = calculate_adx(df)
                
                # 提取最新數據並轉為純純標量 (Scalar)
                latest = df.iloc[-1]
                price = float(latest['Close'])
                adx_val = float(latest['ADX_14'])
                
                # 計算當日 VA 寬度
                today_df = df.loc[df.index.date == df.index[-1].date()]
                high_val = float(today_df['High'].max())
                low_val = float(today_df['Low'].min())
                va_width = ((high_val - low_val) / price) * 100

                # --- 儀表板展示 ---
                c1, c2, c3 = st.columns(3)
                c1.metric("目前價格", f"{price:,.2f}")
                c2.metric("VA 寬度 (估)", f"{va_width:.2f}%")
                c3.metric("ADX 動能", f"{adx_val:.2f}")

                st.divider()

                # --- 邏輯判斷 ---
                if va_width < va_threshold and adx_val < adx_threshold:
                    st.success("### ✅ 判定結果：高盤整環境 (震盪市)")
                    st.info("**決策：鎖定均值回歸劇本**")
                elif va_width >= va_threshold and adx_val >= adx_threshold:
                    st.warning("### ✅ 判定結果：趨勢擴張環境 (趨勢市)")
                    st.error("**決策：開啟順勢追擊劇本**")
                else:
                    st.info("### ✅ 判定結果：市況不明 (過渡期)")
                    st.write("目前 VA 寬度或 ADX 未同時達標，建議觀望。")

                with st.expander("查看原始數據表"):
                    st.dataframe(df.tail(10))

        except Exception as e:
            st.error(f"分析失敗: {str(e)}")
            st.write("技術細節：嘗試將資料強制擠壓（Squeeze）為一維時出錯。")
