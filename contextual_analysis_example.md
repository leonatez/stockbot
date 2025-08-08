# Contextual Analysis Example

## Scenario: HPG Stock Analysis on 2025-01-15

### Direct Stock Mention
**Post**: "HPG báo cáo lợi nhuận Q4 tăng 15%, triển vọng tích cực"
- **Sentiment**: Positive
- **Summary**: HPG reports strong Q4 profit growth

### Contextual Analysis (3 days lookback: 2025-01-12 to 2025-01-14)

#### Industry Context
**Steel Industry Posts**:
1. **Post from 2025-01-13**: "Ngành thép Việt Nam hưởng lợi từ chính sách thuế mới"
   - **Industry**: Steel Industry
   - **Sentiment**: Positive
   - **Summary**: Vietnamese steel industry benefits from new tax policy

2. **Post from 2025-01-12**: "Giá thép thế giới tăng mạnh do thiếu hụt nguồn cung"
   - **Industry**: Steel Industry  
   - **Sentiment**: Positive
   - **Summary**: Global steel prices rise due to supply shortage

#### Macro Economic Context
**Macro Themes from 2025-01-12 to 2025-01-14**:
1. **Market Liquidity** (2025-01-13)
   - **Sentiment**: Positive
   - **Summary**: Market liquidity expected to increase 20% compared to 2024

2. **Corporate Profit Growth** (2025-01-14)
   - **Theme**: Corporate Performance
   - **Indicator**: 11.6% projected growth
   - **Summary**: Overall corporate profits expected to grow strongly

3. **Global Economic Uncertainty** (2025-01-12)
   - **Sentiment**: Negative
   - **Summary**: Geopolitical risks and trade tensions persist

### Enhanced Analysis Result

```json
{
  "stock_analysis": {
    "HPG": {
      "direct_mentions": [
        {
          "post_id": "uuid-123",
          "sentiment": "positive", 
          "summary": "HPG reports strong Q4 profit growth"
        }
      ],
      "contextual_factors": {
        "industry_context": {
          "steel_industry": {
            "sentiment": "positive",
            "strength": 0.85,
            "key_factors": [
              "New tax policy benefits",
              "Global steel price increase",
              "Supply shortage advantages"
            ]
          }
        },
        "macro_context": {
          "supportive_factors": [
            {
              "theme": "Market Liquidity",
              "sentiment": "positive",
              "impact": "Increased trading volume expected"
            },
            {
              "indicator": "Corporate Profit Growth",
              "value": "11.6%",
              "impact": "Sector-wide growth momentum"
            }
          ],
          "risk_factors": [
            {
              "theme": "Global Economic Uncertainty", 
              "sentiment": "negative",
              "impact": "Potential export market challenges"
            }
          ]
        }
      },
      "overall_outlook": {
        "confidence_score": 0.78,
        "recommendation": "Strong positive with monitored risks",
        "summary": "HPG shows strong fundamentals with supportive industry trends and macro conditions, but global uncertainties require monitoring"
      }
    }
  }
}
```

## Database Queries for Contextual Analysis

### 1. Get Industry Context for Stock
```sql
-- Get industry sentiment for stocks in the same industry as HPG
WITH stock_industries AS (
  SELECT DISTINCT i.id, i.name
  FROM industries i
  JOIN stock_industry_mapping sim ON i.id = sim.industry_id  
  WHERE sim.stock_symbol = 'HPG'
),
recent_industry_posts AS (
  SELECT pmi.industry_id, pmi.sentiment, pmi.summary, p.published_date
  FROM post_mentioned_industries pmi
  JOIN posts p ON pmi.post_id = p.id
  JOIN stock_industries si ON pmi.industry_id = si.id
  WHERE p.published_date BETWEEN '2025-01-12' AND '2025-01-14'
)
SELECT * FROM recent_industry_posts;
```

### 2. Get Macro Context for Date Range
```sql
-- Get macro themes sentiment for contextual period
SELECT 
  mt.name as theme_name,
  pmmt.sentiment,
  pmmt.summary,
  p.published_date
FROM post_mentioned_macro_themes pmmt
JOIN macro_themes mt ON pmmt.macro_theme_id = mt.id
JOIN posts p ON pmmt.post_id = p.id
WHERE p.published_date BETWEEN '2025-01-12' AND '2025-01-14'
ORDER BY p.published_date DESC;
```

### 3. Get Macro Indicators
```sql
-- Get specific macro indicators mentioned
SELECT 
  mi.name as indicator_name,
  pmi.current_value,
  pmi.projected_value,
  pmi.time_period,
  p.published_date
FROM post_macro_indicators pmi
JOIN macro_indicators mi ON pmi.macro_indicator_id = mi.id
JOIN posts p ON pmi.post_id = p.id
WHERE p.published_date BETWEEN '2025-01-12' AND '2025-01-14';
```