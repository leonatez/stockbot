# 📊 Stock Trend Detection Signals Cheat Sheet

Tài liệu tổng hợp các tín hiệu kỹ thuật (technical signals) phổ biến trong chứng khoán dùng để nhận diện nhanh xu hướng tăng/giảm (tốt/xấu) của một cổ phiếu.

---

## ✅ 1. Moving Average (MA)

- **Formula**:  
  - MA(n) = Trung bình cộng của `Close` trong n phiên gần nhất  
  - VD: MA50 = Sum(Close[-50:]) / 50
- **Description**:  
  Làm mượt giá để thấy xu hướng trung hạn (trend).
  - MA dốc lên → xu hướng tăng
  - MA dốc xuống → xu hướng giảm
- **Sentiment**:
  - Giá > MA & MA dốc lên → **Good**
  - Giá < MA & MA dốc xuống → **Bad**
  - Giao cắt MA (cắt lên = Golden Cross / cắt xuống = Death Cross)

---

## ✅ 2. Exponential Moving Average (EMA)

- **Formula**:  
  - EMA = Close × α + EMA(prev) × (1 − α), α = 2 / (n + 1)
- **Description**:  
  Giống MA nhưng nhạy hơn với thay đổi gần đây.
- **Sentiment**:
  - Giá > EMA → **Good**
  - Giá < EMA → **Bad**

---

## ✅ 3. RSI (Relative Strength Index)

- **Formula**:
  - RSI = 100 - [100 / (1 + RS)],  
    RS = average gain / average loss (14 phiên mặc định)
- **Description**:
  Đo động lượng giá. Nhận biết quá mua/quá bán.
- **Sentiment**:
  - RSI > 70 → **Bad** (quá mua, dễ đảo chiều giảm)
  - RSI < 30 → **Good** (quá bán, dễ đảo chiều tăng)
  - RSI tăng từ 50–70 → **Good**
  - RSI giảm từ 50–30 → **Bad**

---

## ✅ 4. MACD (Moving Average Convergence Divergence)

- **Formula**:
  - MACD Line = EMA(12) − EMA(26)  
  - Signal Line = EMA(9) của MACD Line
- **Description**:
  Đo độ mạnh và hướng của xu hướng giá.
- **Sentiment**:
  - MACD > 0 và MACD cắt lên Signal → **Good**
  - MACD < 0 và MACD cắt xuống Signal → **Bad**
  - MACD hội tụ/lệch xa → dấu hiệu đảo chiều

---

## ✅ 5. Bollinger Bands

- **Formula**:
  - Middle Band = MA(20)  
  - Upper = MA(20) + 2*StdDev(Close)  
  - Lower = MA(20) − 2*StdDev(Close)
- **Description**:
  Đo biến động và vùng giá cực đoan.
- **Sentiment**:
  - Giá vượt Upper Band → **Neutral/Bad** (quá mua)
  - Giá chạm Lower Band → **Neutral/Good** (quá bán)
  - Band mở rộng → biến động mạnh sắp xảy ra

---

## ✅ 6. Volume

- **Formula**: N/A
- **Description**:
  Xác nhận sức mạnh của xu hướng dựa vào khối lượng.
- **Sentiment**:
  - Giá tăng + Volume tăng → **Good**
  - Giá tăng + Volume giảm → **Neutral/Bad**
  - Giá giảm + Volume tăng → **Bad**

---

## ✅ 7. On-Balance Volume (OBV)

- **Formula**:
  - Nếu Close > Prev Close: OBV += Volume  
  - Nếu Close < Prev Close: OBV -= Volume
- **Description**:
  Cho biết dòng tiền lớn đang vào hay ra khỏi cổ phiếu.
- **Sentiment**:
  - OBV tăng → **Good**
  - OBV giảm → **Bad**
  - OBV lệch pha với giá → có thể sắp đảo chiều

---

## ✅ 8. ADX (Average Directional Index)

- **Formula**:
  - ADX = SMA(14) của |DI+ − DI−| / (DI+ + DI−)
- **Description**:
  Đo độ mạnh của trend (không quan tâm hướng).
- **Sentiment**:
  - ADX > 25 → Có trend rõ ràng (tăng hoặc giảm)
  - ADX < 20 → **Neutral** (thị trường sideway)

---

## ✅ 9. Price Action (Nến, mô hình giá)

- **Formula**: N/A
- **Description**:
  Dựa vào hình dạng nến (Hammer, Engulfing, Doji...), mô hình giá (Double Top, Triangle, Flag...) để đoán xu hướng.
- **Sentiment**:
  - Higher High – Higher Low → **Good**
  - Lower High – Lower Low → **Bad**
  - Nến đảo chiều tăng → **Good**
  - Nến đảo chiều giảm → **Bad**

---

## ✅ 10. Ichimoku Cloud

- **Formula**: (Tổ hợp nhiều MA và vùng giá)
- **Description**:
  Bộ công cụ xác định hỗ trợ, kháng cự và trend toàn diện.
- **Sentiment**:
  - Giá nằm trên mây → **Good**
  - Giá nằm dưới mây → **Bad**
  - Giá đi ngang trong mây → **Neutral**

---

> **Lưu ý:** Các chỉ báo không nên dùng đơn lẻ. Cần kết hợp nhiều signal để xác nhận xu hướng.

