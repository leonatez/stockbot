# Macro Economy Tables Workflow Example

## Scenario: Crawling ACBS Strategic Report

### Step 1: Source Configuration
```json
// User configures macro economy source
{
  "name": "ACBS Strategic Analysis",
  "source_type": "macro_economy",  // NEW field
  "base_url": "https://acbs.com.vn/trung-tam-phan-tich/",
  "post_links_xpath": "//a[contains(@href, 'chi-tiet')]",
  "content_xpath": "//div[@class='content-detail']",
  "date_xpath": "//span[@class='date']"
}
```

### Step 2: Crawl and Extract Post
```json
// Post data extracted from ACBS report
{
  "title": "Báo cáo chiến lược 6 tháng cuối năm 2025",
  "content": "Trong bối cảnh kinh tế toàn cầu bất ổn... VN Index dao động 1,230-1,341 trong Q1 2025... Lợi nhuận ròng doanh nghiệp dự kiến tăng 11.6%... Chính sách tiền tệ thắt chặt với lãi suất cao...",
  "url": "https://acbs.com.vn/trung-tam-phan-tich/chi-tiet/bao-cao-chien-luoc-6-thang-cuoi-nam-2025",
  "published_date": "2025-01-15"
}
```

### Step 3: Gemini AI Analysis

#### Analysis Prompt for Macro Economy
```python
analyze_macro_prompt = """
Phân tích bài báo cáo kinh tế vĩ mô tiếng Việt và trích xuất:

1. CÁC CHỦ ĐỀ KINH TẾ VĨ MÔ được đề cập:
   - Từ danh sách: ["global_economy", "monetary_policy", "market_liquidity", "corporate_performance", "geopolitical_risk", "fiscal_policy", "inflation", "exchange_rate"]
   - Cho mỗi chủ đề: sentiment (positive/negative/neutral), summary, confidence (0-1)

2. CÁC CHỈ SỐ KINH TẾ CỤ THỂ:
   - VN Index dự báo, tăng trưởng lợi nhuận doanh nghiệp, lãi suất, tỷ lệ P/E, v.v.
   - Cho mỗi chỉ số: giá trị hiện tại, giá trị dự báo, khoảng thời gian

Trả về JSON format.
"""
```

#### Gemini Response
```json
{
  "macro_themes": [
    {
      "theme_id": "global_economy",
      "sentiment": "negative", 
      "summary": "Kinh tế toàn cầu bất ổn với rủi ro địa chính trị và chiến tranh thương mại kéo dài",
      "confidence": 0.9
    },
    {
      "theme_id": "monetary_policy",
      "sentiment": "negative",
      "summary": "Chính sách tiền tệ thắt chặt với lãi suất cao gây áp lực lên thị trường",
      "confidence": 0.85
    },
    {
      "theme_id": "market_liquidity", 
      "sentiment": "positive",
      "summary": "Thanh khoản thị trường dự kiến tăng 20% so với 2024",
      "confidence": 0.8
    },
    {
      "theme_id": "corporate_performance",
      "sentiment": "positive",
      "summary": "Lợi nhuận doanh nghiệp có triển vọng tăng trưởng tốt",
      "confidence": 0.9
    }
  ],
  "macro_indicators": [
    {
      "indicator_id": "vn_index_forecast",
      "current_value": "1,230-1,341",
      "projected_value": "1,350-1,500", 
      "time_period": "6 months 2025",
      "context": "VN Index dao động trong khoảng này dựa trên thanh khoản tăng"
    },
    {
      "indicator_id": "corporate_profit_growth",
      "current_value": null,
      "projected_value": "11.6%",
      "time_period": "2025", 
      "context": "Lợi nhuận ròng doanh nghiệp dự kiến tăng trưởng"
    },
    {
      "indicator_id": "market_pe_ratio",
      "current_value": "-1 standard deviation",
      "projected_value": null,
      "time_period": "current",
      "context": "Định giá thị trường ở mức thấp hơn trung bình"
    }
  ]
}
```

### Step 4: Database Storage

#### Insert into Tables
```sql
-- 1. Insert post
INSERT INTO posts (id, source_id, title, content, url, published_date)
VALUES ('uuid-post-123', 'uuid-acbs-source', 'Báo cáo chiến lược...', '...', 'https://acbs.com.vn/...', '2025-01-15');

-- 2. Insert macro themes mentions
INSERT INTO post_mentioned_macro_themes (post_id, macro_theme_id, sentiment, summary, confidence_score)
VALUES 
  ('uuid-post-123', 'global_economy', 'negative', 'Kinh tế toàn cầu bất ổn...', 0.9),
  ('uuid-post-123', 'monetary_policy', 'negative', 'Chính sách tiền tệ thắt chặt...', 0.85),
  ('uuid-post-123', 'market_liquidity', 'positive', 'Thanh khoản thị trường...', 0.8),
  ('uuid-post-123', 'corporate_performance', 'positive', 'Lợi nhuận doanh nghiệp...', 0.9);

-- 3. Insert macro indicators
INSERT INTO post_macro_indicators (post_id, macro_indicator_id, current_value, projected_value, time_period, mentioned_context)
VALUES
  ('uuid-post-123', 'vn_index_forecast', '1,230-1,341', '1,350-1,500', '6 months 2025', 'VN Index dao động...'),
  ('uuid-post-123', 'corporate_profit_growth', null, '11.6%', '2025', 'Lợi nhuận ròng...'),
  ('uuid-post-123', 'market_pe_ratio', '-1 standard deviation', null, 'current', 'Định giá thị trường...');
```

### Step 5: How It Works in Stock Analysis

#### When analyzing HPG stock on 2025-01-18, look back 3 days (2025-01-15 to 2025-01-17)

```python
def get_macro_context_for_stock(analysis_date, lookback_days=3):
    context_start = analysis_date - timedelta(days=lookback_days)
    
    # Get macro themes sentiment
    macro_themes = db.execute("""
        SELECT 
            mt.name,
            pmmt.sentiment,
            pmmt.summary,
            pmmt.confidence_score,
            p.published_date
        FROM post_mentioned_macro_themes pmmt
        JOIN macro_themes mt ON pmmt.macro_theme_id = mt.id  
        JOIN posts p ON pmmt.post_id = p.id
        WHERE p.published_date BETWEEN %s AND %s
          AND p.source_id IN (SELECT id FROM sources WHERE source_type = 'macro_economy')
        ORDER BY pmmt.confidence_score DESC
    """, [context_start, analysis_date])
    
    # Get macro indicators
    macro_indicators = db.execute("""
        SELECT 
            mi.name,
            pmi.current_value,
            pmi.projected_value, 
            pmi.time_period,
            p.published_date
        FROM post_macro_indicators pmi
        JOIN macro_indicators mi ON pmi.macro_indicator_id = mi.id
        JOIN posts p ON pmi.post_id = p.id
        WHERE p.published_date BETWEEN %s AND %s
    """, [context_start, analysis_date])
    
    return {
        "themes": macro_themes,
        "indicators": macro_indicators
    }
```

#### Enhanced Stock Analysis Result
```json
{
  "stock_analysis": {
    "HPG": {
      "direct_mentions": [
        {"sentiment": "positive", "summary": "HPG báo lợi nhuận Q4 tăng 15%"}
      ],
      "contextual_factors": {
        "macro_environment": {
          "themes": [
            {
              "name": "Market Liquidity",
              "sentiment": "positive", 
              "impact": "Thanh khoản tăng 20% hỗ trợ giao dịch HPG",
              "confidence": 0.8
            },
            {
              "name": "Corporate Performance", 
              "sentiment": "positive",
              "impact": "Xu hướng tăng trưởng lợi nhuận chung 11.6%",
              "confidence": 0.9
            },
            {
              "name": "Global Economy",
              "sentiment": "negative",
              "impact": "Rủi ro xuất khẩu thép do bất ổn toàn cầu", 
              "confidence": 0.9
            }
          ],
          "indicators": [
            {
              "name": "VN Index Forecast",
              "current": "1,230-1,341",
              "projected": "1,350-1,500",
              "impact": "Thị trường tổng thể tích cực hỗ trợ HPG"
            },
            {
              "name": "Market P/E Ratio", 
              "current": "-1 standard deviation",
              "impact": "Thị trường đang định giá thấp, có cơ hội tăng"
            }
          ]
        }
      },
      "overall_assessment": {
        "macro_support_score": 0.65, // Weighted by confidence scores
        "key_risks": ["Global economic uncertainty"],
        "key_opportunities": ["Increased market liquidity", "Low market valuation"]
      }
    }
  }
}
```

## Pre-populated Master Data

### Macro Categories & Themes
```sql
-- Categories
INSERT INTO macro_categories VALUES
  ('global_economy', 'Kinh tế Toàn cầu', 'Global Economy'),
  ('monetary_policy', 'Chính sách Tiền tệ', 'Monetary Policy'),  
  ('market_conditions', 'Điều kiện Thị trường', 'Market Conditions'),
  ('corporate_sector', 'Khu vực Doanh nghiệp', 'Corporate Sector');

-- Themes  
INSERT INTO macro_themes VALUES
  ('market_liquidity', 'market_conditions', 'Thanh khoản Thị trường', 'Market Liquidity'),
  ('corporate_performance', 'corporate_sector', 'Hiệu suất Doanh nghiệp', 'Corporate Performance'),
  ('global_uncertainty', 'global_economy', 'Bất ổn Toàn cầu', 'Global Uncertainty');

-- Indicators
INSERT INTO macro_indicators VALUES
  ('vn_index_forecast', 'market_liquidity', 'Dự báo VN Index', 'VN Index Forecast', 'points', 'range'),
  ('corporate_profit_growth', 'corporate_performance', 'Tăng trưởng Lợi nhuận', 'Corporate Profit Growth', '%', 'percentage');
```

## Key Benefits

1. **Structured Macro Analysis**: Convert unstructured macro reports into structured data
2. **Contextual Stock Intelligence**: Stock analysis enhanced with macro backdrop  
3. **Quantified Indicators**: Specific forecasts and metrics for decision support
4. **Confidence Weighting**: Prioritize high-confidence macro insights
5. **Temporal Context**: 3-day lookback provides relevant macro environment for any stock analysis

This approach transforms macro economy reports into actionable context for individual stock analysis decisions.